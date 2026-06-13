/**
 * Connections 페이지 — PG-01 (/connections) / FR-01, FR-02.
 * 커넥션 목록(테스트/사용/삭제) + 신규 연결 위저드:
 *   ① 경로 분기 [wallet zip 업로드 | OCI CLI 자동 다운로드(조회중→다운로드중→해제중,
 *      409 후보 선택, 424 CLI 미설치 → 업로드 폴백)]
 *   ② TNS alias 선택 + admin 비밀번호
 *   ③ 접속 테스트 → 저장 (api-spec §2.2 — validate=true 생성이 곧 테스트+저장)
 * 설계 근거: design.md PG-01, api-spec §2.
 */
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError, deleteEnvelope, getEnvelope, postEnvelope } from "../api/client";
import type {
  AdbCandidate,
  ConnectionOut,
  ConnectionTestResult,
  WalletGenerateResult,
  WalletUploadResult,
} from "../api/types";
import Button from "../components/Button";
import Field from "../components/Field";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

/** CLAUDE.md 전역 규칙 — 모든 OCI 작업 기본 컴파트먼트 (TAEWAN.KIM) */
const DEFAULT_COMPARTMENT_ID =
  "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq";

/** TNS alias 레벨별 한국어 해설 (design.md PG-01 ② 단계) */
function aliasHint(alias: string): string {
  const lower = alias.toLowerCase();
  if (lower.endsWith("_high")) return "최고 성능, 동시성 낮음";
  if (lower.endsWith("_medium")) return "균형 (데모 권장)";
  if (lower.endsWith("_low")) return "동시성 높음";
  if (lower.endsWith("_tpurgent")) return "트랜잭션 우선·최고 우선순위";
  if (lower.endsWith("_tp")) return "트랜잭션 처리용";
  return "";
}

/** 자동 다운로드 진행 단계 (api-spec §2.7 — 조회 30초 / 다운로드 120초) */
type GeneratePhase = "idle" | "lookup" | "download" | "extract";

const PHASE_LABEL: Record<Exclude<GeneratePhase, "idle">, string> = {
  lookup: "조회중",
  download: "다운로드중",
  extract: "해제중",
};

export function Connections() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeConnectionId, setActiveConnection } = useConnectionStore();

  // ---------------------------------------------------------------- 목록
  const { data: connections, isLoading: listLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: async () => (await getEnvelope<ConnectionOut[]>("/connections")).data,
  });

  // 행별 테스트 결과 (커넥션 ID → 진단 결과)
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({});

  const testMutation = useMutation({
    mutationFn: async (id: string) =>
      (await postEnvelope<ConnectionTestResult>(`/connections/${id}/test`)).data,
    onSuccess: (result, id) => setTestResults((prev) => ({ ...prev, [id]: result })),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => deleteEnvelope(`/connections/${id}`),
    onSuccess: (_res, id) => {
      if (activeConnectionId === id) setActiveConnection(null);
      void queryClient.invalidateQueries({ queryKey: ["connections"] });
    },
  });

  // ---------------------------------------------------------------- 위저드 상태
  const [wizardOpen, setWizardOpen] = useState(false);
  const [walletPath, setWalletPath] = useState<"upload" | "generate">("upload");

  // ① 공통 결과 — 두 경로가 여기로 합류 (design.md PG-01)
  const [walletResult, setWalletResult] = useState<WalletUploadResult | null>(null);

  // ②/③ 입력
  const [tnsAlias, setTnsAlias] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [connName, setConnName] = useState("");

  // ---------------------------------------------------------------- ①-a 업로드
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // wallet zip은 multipart/form-data — 공유 인터셉터(executed_sql 누적)는 그대로 동작
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<{ data: WalletUploadResult }>("/connections/wallet", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data.data;
    },
    onSuccess: (result) => {
      setWalletResult(result);
      // 데모 권장 medium을 기본 선택, 없으면 첫 alias (design.md PG-01 ②)
      const preferred =
        result.tns_aliases.find((a) => a.toLowerCase().endsWith("_medium")) ??
        result.tns_aliases[0] ??
        "";
      setTnsAlias(preferred);
    },
  });

  const handleFile = (file: File | undefined) => {
    if (file) uploadMutation.mutate(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  // ---------------------------------------------------------------- ①-b 자동 다운로드
  const [adbName, setAdbName] = useState("");
  const [walletPassword, setWalletPassword] = useState("");
  const [compartmentId, setCompartmentId] = useState(DEFAULT_COMPARTMENT_ID);
  const [ociProfile, setOciProfile] = useState("DEFAULT");
  const [candidates, setCandidates] = useState<AdbCandidate[] | null>(null);
  const [phase, setPhase] = useState<GeneratePhase>("idle");

  // 진행 단계는 단일 요청이라 서버 이벤트가 없다 — §2.7 단계 타임아웃(조회 30초)에 맞춘
  // 클라이언트 측 시간 기반 추정 표시 (가정: 30초 경과 시 다운로드 단계로 진입했다고 간주)
  useEffect(() => {
    if (phase !== "lookup") return;
    const t = setTimeout(() => setPhase("download"), 30_000);
    return () => clearTimeout(t);
  }, [phase]);

  const generateMutation = useMutation({
    mutationFn: async (adbOcid: string | null) => {
      setPhase("lookup");
      const envelope = await postEnvelope<WalletGenerateResult>("/connections/wallet/generate", {
        adb_name: adbName,
        wallet_password: walletPassword,
        compartment_id: compartmentId || undefined,
        oci_profile: ociProfile || undefined,
        adb_ocid: adbOcid,
      });
      return envelope.data;
    },
    onSuccess: (result) => {
      // 응답 직전 단계는 해제중 — 합류 직후 idle 복귀
      setPhase("idle");
      setCandidates(null);
      setWalletResult(result);
      const preferred =
        result.tns_aliases.find((a) => a.toLowerCase().endsWith("_medium")) ??
        result.tns_aliases[0] ??
        "";
      setTnsAlias(preferred);
    },
    onError: (error) => {
      setPhase("idle");
      // 409 ADB_AMBIGUOUS — 후보 목록에서 선택 후 adb_ocid로 재호출 (api-spec §2.7)
      if (error instanceof ApiError && error.body.app_code === "ADB_AMBIGUOUS") {
        setCandidates(error.body.candidates ?? []);
      }
    },
  });

  const generateError =
    generateMutation.error instanceof ApiError ? generateMutation.error.body : null;
  // 424 CLI 미설치 / 401 인증 실패 — 업로드 폴백 유도 (design.md PG-01 ①-b)
  const cliUnavailable =
    generateError?.app_code === "OCI_CLI_NOT_FOUND" ||
    generateError?.app_code === "OCI_CLI_AUTH_FAILED";

  // ---------------------------------------------------------------- ③ 테스트→저장
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!walletResult) throw new Error("wallet이 준비되지 않았습니다");
      // validate=true — 접속 테스트에 성공해야만 저장된다 (api-spec §2.2)
      const envelope = await postEnvelope<ConnectionOut>("/connections", {
        name: connName,
        wallet_id: walletResult.wallet_id,
        tns_alias: tnsAlias,
        username: "admin",
        password,
        validate: true,
      });
      return envelope.data;
    },
    onSuccess: (created) => {
      setActiveConnection(created);
      void queryClient.invalidateQueries({ queryKey: ["connections"] });
    },
  });

  const resetWizard = () => {
    setWalletResult(null);
    setTnsAlias("");
    setPassword("");
    setConnName("");
    setCandidates(null);
    uploadMutation.reset();
    generateMutation.reset();
    createMutation.reset();
  };

  const uploadError = uploadMutation.error instanceof ApiError ? uploadMutation.error.body : null;
  const createError = createMutation.error instanceof ApiError ? createMutation.error.body : null;
  const created = createMutation.data ?? null;

  // ---------------------------------------------------------------- 렌더
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">커넥션 관리</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            wallet zip 업로드(또는 OCI 자동 다운로드), admin 접속 검증, 저장된 커넥션 재사용을 한
            화면에서 처리합니다.
          </p>
        </div>
        <Button
          onClick={() => {
            resetWizard();
            setWizardOpen(true);
          }}
        >
          + 새 연결
        </Button>
      </div>

      {/* ------------------------------------------------ 신규 연결 위저드 */}
      {wizardOpen ? (
        <Panel
          title={
            <span className="flex items-center justify-between gap-3">
              <span>새 연결 위저드</span>
              <span className="text-xs font-normal text-[var(--color-neutral-60)]">
                ① wallet → ② 접속 정보 → ③ 테스트·저장
              </span>
            </span>
          }
        >
          {/* ① 경로 분기 */}
          <fieldset className="mb-4 flex gap-6 text-sm">
            <legend className="mb-2 font-medium">① 경로 선택</legend>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="wallet-path"
                checked={walletPath === "upload"}
                onChange={() => setWalletPath("upload")}
              />
              wallet zip 업로드
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="wallet-path"
                checked={walletPath === "generate"}
                onChange={() => setWalletPath("generate")}
              />
              Wallet이 없으신가요? OCI에서 자동 다운로드
            </label>
          </fieldset>

          {/* ①-a 업로드 경로 */}
          {walletPath === "upload" && !walletResult ? (
            <div>
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                className={`flex h-32 cursor-pointer items-center justify-center rounded-[var(--radius-lg)] border-2 border-dashed text-sm ${
                  dragOver
                    ? "border-[var(--color-brand)] bg-[var(--color-info-tint)]"
                    : "border-[var(--color-neutral-40)] bg-[var(--color-neutral-10)]"
                }`}
              >
                {uploadMutation.isPending
                  ? "업로드·검증 중…"
                  : "Wallet_xxx.zip을 끌어다 놓거나 클릭해서 업로드 (최대 5 MB)"}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleFile(e.target.files?.[0])}
              />
              {uploadError ? (
                <ErrorCard
                  messageKo={uploadError.message_ko}
                  hintKo={uploadError.hint_ko}
                  detail={uploadError.detail}
                />
              ) : null}
            </div>
          ) : null}

          {/* ①-b 자동 다운로드 경로 */}
          {walletPath === "generate" && !walletResult ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <Field
                  id="adb-name"
                  label="ADB 이름 (표시 이름)"
                  value={adbName}
                  onChange={(e) => setAdbName(e.target.value)}
                  placeholder="DEMOADB"
                />
                <Field
                  id="wallet-password"
                  label="wallet 암호"
                  type="password"
                  value={walletPassword}
                  onChange={(e) => setWalletPassword(e.target.value)}
                  helpKo="다운로드되는 wallet zip에 설정할 암호입니다. 응답·로그에 평문 노출되지 않습니다."
                />
                <Field
                  id="compartment-id"
                  label="컴파트먼트 OCID"
                  value={compartmentId}
                  onChange={(e) => setCompartmentId(e.target.value)}
                  helpKo="기본값: TAEWAN.KIM 컴파트먼트 — 변경 가능"
                />
                <Field
                  id="oci-profile"
                  label="OCI CLI 프로파일"
                  value={ociProfile}
                  onChange={(e) => setOciProfile(e.target.value)}
                  helpKo="~/.oci/config의 프로파일 이름 (기본 DEFAULT)"
                />
              </div>

              <div className="flex items-center gap-4">
                <Button
                  onClick={() => generateMutation.mutate(null)}
                  loading={generateMutation.isPending}
                  disabled={!adbName || !walletPassword}
                >
                  다운로드 시작
                </Button>
                {/* 진행 3단계 표시 — 수십 초 걸릴 수 있음 안내 (design.md PG-01) */}
                {generateMutation.isPending ? (
                  <span className="flex items-center gap-2 text-sm text-[var(--color-neutral-60)]">
                    {(["lookup", "download", "extract"] as const).map((p, i) => (
                      <span key={p} className="flex items-center gap-2">
                        {i > 0 ? <span>→</span> : null}
                        <span
                          className={
                            phase === p ? "font-semibold text-[var(--color-running)]" : ""
                          }
                        >
                          {PHASE_LABEL[p]}
                          {phase === p ? " ◌" : ""}
                        </span>
                      </span>
                    ))}
                    <span className="ml-2">(수십 초 걸릴 수 있습니다)</span>
                  </span>
                ) : null}
              </div>

              {/* 409 — ADB 후보 선택 UI */}
              {candidates ? (
                <Panel variant="explain" title="같은 이름의 ADB가 여러 개 발견되었습니다 — 하나를 선택하세요">
                  <ul className="flex flex-col gap-2">
                    {candidates.map((c) => (
                      <li key={c.adb_ocid}>
                        <button
                          className="w-full rounded-[var(--radius-md)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-3 py-2 text-left text-sm hover:border-[var(--color-brand)]"
                          onClick={() => generateMutation.mutate(c.adb_ocid)}
                        >
                          <strong>{c.display_name}</strong>
                          {c.workload_type ? ` · ${c.workload_type}` : ""}
                          <span className="ml-2 break-all text-xs text-[var(--color-neutral-60)]">
                            {c.adb_ocid}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </Panel>
              ) : null}

              {/* CLI 미설치/인증 실패 — 한국어 안내 + 업로드 폴백 */}
              {generateError && !candidates ? (
                <ErrorCard
                  messageKo={generateError.message_ko}
                  hintKo={generateError.hint_ko}
                  detail={generateError.detail}
                  action={
                    cliUnavailable ? (
                      <Button variant="secondary" onClick={() => setWalletPath("upload")}>
                        업로드로 전환
                      </Button>
                    ) : generateError.retryable ? (
                      <Button variant="secondary" onClick={() => generateMutation.mutate(null)}>
                        재시도
                      </Button>
                    ) : undefined
                  }
                />
              ) : null}
            </div>
          ) : null}

          {/* wallet 합류 후 — 검증 체크리스트 + ② ③ */}
          {walletResult ? (
            <div className="mt-2 flex flex-col gap-5">
              {/* zip 내용 검증 결과 체크리스트 */}
              <div className="flex flex-wrap gap-2">
                {walletResult.files_found.map((f) => (
                  <StatusBadge key={f} status="success">
                    {f} 발견 ✓
                  </StatusBadge>
                ))}
                <Button variant="ghost" onClick={resetWizard}>
                  wallet 다시 선택
                </Button>
              </div>

              {/* ② TNS alias + admin 비밀번호 */}
              <fieldset>
                <legend className="mb-2 text-sm font-medium">② TNS 서비스 (zip에서 자동 추출)</legend>
                <div className="flex flex-col gap-1">
                  {walletResult.tns_aliases.map((alias) => (
                    <label key={alias} className="flex cursor-pointer items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="tns-alias"
                        checked={tnsAlias === alias}
                        onChange={() => setTnsAlias(alias)}
                      />
                      <code>{alias}</code>
                      {aliasHint(alias) ? (
                        <span className="text-xs text-[var(--color-neutral-60)]">
                          — {aliasHint(alias)}
                        </span>
                      ) : null}
                    </label>
                  ))}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <Field id="db-user" label="사용자" value="admin" readOnly helpKo="v1에서는 admin 고정입니다." />
                  <div className="relative">
                    <Field
                      id="db-password"
                      label="admin 비밀번호"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      className="absolute right-2 top-8 text-xs text-[var(--color-link)]"
                      onClick={() => setShowPassword((v) => !v)}
                    >
                      {showPassword ? "숨김" : "표시"}
                    </button>
                  </div>
                </div>
              </fieldset>

              {/* ③ 테스트·저장 */}
              <fieldset>
                <legend className="mb-2 text-sm font-medium">③ 접속 테스트 후 저장</legend>
                <div className="flex items-end gap-3">
                  <Field
                    id="conn-name"
                    label="커넥션 이름"
                    value={connName}
                    onChange={(e) => setConnName(e.target.value)}
                    placeholder="demo-adb-26ai"
                    className="w-72"
                  />
                  <Button
                    onClick={() => createMutation.mutate()}
                    loading={createMutation.isPending}
                    disabled={!tnsAlias || !password || !connName}
                  >
                    접속 테스트 후 저장
                  </Button>
                </div>
                {createMutation.isPending ? (
                  <p className="mt-2 text-sm text-[var(--color-running)]">접속 시도 중… (최대 5초)</p>
                ) : null}
                {/* 검증 시 내부 SQL 미리보기 (api-spec §2.2 — 교육적 투명성 원칙 1) */}
                <div className="mt-2">
                  <SqlBlock
                    preview
                    label="테스트 시 실행될 SQL 보기"
                    sql={[
                      "SELECT banner_full FROM v$version WHERE ROWNUM = 1;",
                      "SELECT sys_context('USERENV','CURRENT_USER')  AS current_user,\n       sys_context('USERENV','DB_NAME')       AS db_name,\n       sys_context('USERENV','SERVICE_NAME')  AS service_name\n  FROM dual;",
                    ]}
                  />
                </div>

                {created ? (
                  <div className="mt-3 rounded-[var(--radius-md)] bg-[var(--color-success-tint)] p-4 text-sm">
                    <p className="font-semibold text-[var(--color-success)]">
                      ✓ 접속 성공 — {created.db_version ?? "버전 미상"} / 인스턴스{" "}
                      {created.db_name ?? "-"} / 현재 사용자 {created.username}
                    </p>
                    <div className="mt-3 flex gap-3">
                      <Button onClick={() => navigate("/permissions")}>권한 점검을 시작할까요? →</Button>
                      <Button variant="secondary" onClick={() => setWizardOpen(false)}>
                        목록으로
                      </Button>
                    </div>
                  </div>
                ) : null}
                {createError ? (
                  <ErrorCard
                    messageKo={createError.message_ko}
                    hintKo={createError.hint_ko}
                    detail={createError.detail}
                    action={
                      createError.retryable ? (
                        <Button variant="secondary" onClick={() => createMutation.mutate()}>
                          재시도
                        </Button>
                      ) : undefined
                    }
                  />
                ) : null}
              </fieldset>
            </div>
          ) : null}

          {!created ? (
            <div className="mt-4 text-right">
              <Button variant="ghost" onClick={() => setWizardOpen(false)}>
                위저드 닫기
              </Button>
            </div>
          ) : null}
        </Panel>
      ) : null}

      {/* ------------------------------------------------ 저장된 커넥션 목록 */}
      <Panel title="저장된 커넥션">
        {listLoading ? (
          <p className="text-sm text-[var(--color-neutral-60)]">목록 불러오는 중…</p>
        ) : !connections || connections.length === 0 ? (
          <p className="text-sm text-[var(--color-neutral-60)]">
            저장된 커넥션이 없습니다. [+ 새 연결]로 wallet zip을 업로드하세요.
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--color-neutral-30)]">
            {connections.map((conn) => {
              const test = testResults[conn.id];
              const isActive = conn.id === activeConnectionId;
              return (
                <li key={conn.id} className="flex flex-col gap-2 py-3">
                  <div className="flex items-center gap-3">
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{
                        background:
                          conn.status === "VALID"
                            ? "var(--color-success)"
                            : conn.status === "INVALID"
                              ? "var(--color-danger)"
                              : "var(--color-neutral-50)",
                      }}
                    />
                    <span className="font-semibold">{conn.name}</span>
                    <code className="text-sm text-[var(--color-neutral-60)]">{conn.tns_alias}</code>
                    <span className="text-sm text-[var(--color-neutral-60)]">{conn.username}</span>
                    {isActive ? <StatusBadge status="info">사용 중</StatusBadge> : null}
                    <span className="ml-auto flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => testMutation.mutate(conn.id)}
                        loading={testMutation.isPending && testMutation.variables === conn.id}
                      >
                        테스트
                      </Button>
                      <Button variant="secondary" onClick={() => setActiveConnection(conn)}>
                        사용
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => {
                          // 파괴적 작업 2단계 — 확인 다이얼로그 (인터랙션 원칙 5)
                          if (window.confirm(`커넥션 '${conn.name}'을(를) 삭제할까요? 저장된 자격 정보와 풀이 제거됩니다.`)) {
                            deleteMutation.mutate(conn.id);
                          }
                        }}
                        loading={deleteMutation.isPending && deleteMutation.variables === conn.id}
                      >
                        삭제
                      </Button>
                    </span>
                  </div>
                  <p className="pl-6 text-xs text-[var(--color-neutral-60)]">
                    마지막 사용: {conn.last_used_at ?? "기록 없음"}
                  </p>
                  {test ? (
                    test.ok ? (
                      <p className="pl-6 text-sm text-[var(--color-success)]">
                        ✓ 접속 성공 — {test.db_version ?? ""} ({test.latency_ms ?? "?"}ms)
                      </p>
                    ) : (
                      <div className="pl-6">
                        <ErrorCard
                          messageKo={`테스트 실패: ${test.message_ko ?? test.app_code ?? "알 수 없는 오류"}`}
                          hintKo={test.hint_ko}
                        />
                      </div>
                    )
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}

/** 오류 친화 카드 — 한국어 원인 + 조치 + 원문 접기 (design.md §4 오류 친화 카드) */
function ErrorCard({
  messageKo,
  hintKo,
  detail,
  action,
}: {
  messageKo: string;
  hintKo?: string | null;
  detail?: string | null;
  action?: ReactNode;
}) {
  return (
    <div className="mt-2 rounded-[var(--radius-md)] bg-[var(--color-danger-tint)] p-3 text-sm">
      <p className="font-medium text-[var(--color-danger)]">{messageKo}</p>
      {hintKo ? <p className="mt-1 text-[var(--color-neutral-70)]">→ 조치: {hintKo}</p> : null}
      {detail ? (
        <details className="mt-1">
          <summary className="cursor-pointer text-xs text-[var(--color-neutral-60)]">오류 원문 보기</summary>
          <pre className="mt-1 whitespace-pre-wrap text-xs">{detail}</pre>
        </details>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export default Connections;
