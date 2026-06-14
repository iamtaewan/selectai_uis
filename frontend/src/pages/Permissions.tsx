/**
 * Permissions 페이지 — PG-02 (/permissions) / FR-03.
 * GET /privileges/check 신호등 체크리스트 + 항목별 fix_sql 미리보기 +
 * 원클릭 적용(POST /privileges/apply, recheck=true → 자동 재점검).
 * provider=oci(기본)면 네트워크 ACL은 "필요 없음(해당없음)" (design.md 설계 전제 4).
 * 설계 근거: design.md PG-02, api-spec §3.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, getEnvelope, postEnvelope } from "../api/client";
import type {
  CheckStatus,
  CredentialSpec,
  OciCliDefaults,
  PrivilegeApplyItem,
  PrivilegeApplyResult,
  PrivilegeCheck,
  PrivilegeCheckResult,
} from "../api/types";
import Button from "../components/Button";
import Field from "../components/Field";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

/** 점검 분기 기준 AI 공급자 (api-spec §3.1 — 기본 oci) */
const PROVIDERS = ["oci", "openai", "azure", "google", "cohere", "anthropic", "aws"] as const;

const STATUS_BADGE: Record<CheckStatus, { badge: "success" | "error" | "neutral" | "warning"; label: string }> = {
  pass: { badge: "success", label: "통과" },
  fail: { badge: "error", label: "미충족" },
  not_applicable: { badge: "neutral", label: "필요 없음" },
  unknown: { badge: "warning", label: "확인 불가" },
};

export function Permissions() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const activeConnection = useConnectionStore((s) => s.activeConnection);

  const [provider, setProvider] = useState<(typeof PROVIDERS)[number]>("oci");
  // credential 항목 — API 서명 키(User Principal) 폼 (방법 B 폴백, O1 결정: Resource Principal 권장)
  const [credFormOpen, setCredFormOpen] = useState(false);
  const [cred, setCred] = useState<CredentialSpec>({
    credential_name: "GENAI_CRED",
    auth_type: "api_key",
    user_ocid: "",
    tenancy_ocid: "",
    private_key: "",
    fingerprint: "",
  });

  // ~/.oci/config + api-key.pem 기반 User Principal 폼 기본값 (DB 비의존 — 로컬 파일)
  const { data: ociDefaults } = useQuery({
    queryKey: ["privileges", "oci-defaults"],
    queryFn: async () =>
      (await getEnvelope<OciCliDefaults>("/privileges/oci-defaults", undefined, {
        suppressErrorToast: true,
      })).data,
    staleTime: Infinity,
  });
  const [ociPrefilled, setOciPrefilled] = useState(false);

  // 기본값이 있고(available) 아직 사용자가 입력하지 않았다면 폼을 자동 채움 (없으면 생략)
  const applyOciDefaults = (d: OciCliDefaults) =>
    setCred((prev) => ({
      ...prev,
      auth_type: "api_key",
      user_ocid: d.user_ocid ?? prev.user_ocid,
      tenancy_ocid: d.tenancy_ocid ?? prev.tenancy_ocid,
      fingerprint: d.fingerprint ?? prev.fingerprint,
      private_key: d.private_key ?? prev.private_key,
    }));

  useEffect(() => {
    if (ociDefaults?.available && !ociPrefilled) {
      applyOciDefaults(ociDefaults);
      setOciPrefilled(true);
    }
  }, [ociDefaults, ociPrefilled]);

  const queryKey = ["privileges", "check", provider];
  const {
    data: result,
    isLoading,
    isFetching,
    error: checkError,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: async () =>
      (
        await getEnvelope<PrivilegeCheckResult>("/privileges/check", {
          provider,
          target_user: "ADMIN",
        })
      ).data,
    enabled: !!activeConnection,
  });

  const applyMutation = useMutation({
    mutationFn: async (items: PrivilegeApplyItem[]) =>
      (
        await postEnvelope<PrivilegeApplyResult>("/privileges/apply", {
          provider,
          target_user: "ADMIN",
          items,
          recheck: true, // 적용 후 자동 재점검 (FR-03 수용 기준)
        })
      ).data,
    onSuccess: (applied) => {
      // recheck 결과로 캐시 즉시 갱신 → 재점검 왕복 절약, 없으면 invalidate
      if (applied.recheck) {
        queryClient.setQueryData(queryKey, applied.recheck);
      } else {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
  });

  /** 항목 → 적용 요청 페이로드 변환 (credential은 폼 값, data_access는 enable=true) */
  const toApplyItem = (check: PrivilegeCheck): PrivilegeApplyItem => {
    if (check.check_id === "credential") return { check_id: check.check_id, credential: cred };
    if (check.check_id === "data_access") return { check_id: check.check_id, enable: true };
    return { check_id: check.check_id };
  };

  /** 제거(해제) 실행 — resource_principal / credential. 미리보기는 화면에, 실행 전 확인. */
  const removeItem = (check: PrivilegeCheck) => {
    const label =
      check.check_id === "resource_principal" ? "Resource Principal 해제" : "credential 제거";
    if (!window.confirm(`${label}을(를) 실행할까요? 이 작업은 DB에 즉시 반영됩니다.`)) return;
    const item: PrivilegeApplyItem = { check_id: check.check_id, operation: "remove" };
    if (check.check_id === "credential") item.credential_name = cred.credential_name;
    applyMutation.mutate([item]);
  };

  const failedChecks = result?.checks.filter((c) => c.status === "fail") ?? [];
  const passCount = result?.checks.filter((c) => c.status === "pass").length ?? 0;
  const applicableCount =
    result?.checks.filter((c) => c.status === "pass" || c.status === "fail").length ?? 0;
  const applyError = applyMutation.error instanceof ApiError ? applyMutation.error.body : null;

  if (!activeConnection) {
    return (
      <Panel title="권한 사전 점검">
        <p className="text-sm text-[var(--color-neutral-60)]">
          먼저 커넥션을 연결하세요.{" "}
          <button className="text-[var(--color-link)] underline" onClick={() => navigate("/connections")}>
            ① 커넥션으로 이동
          </button>
        </p>
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">권한 사전 점검</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            대상: {activeConnection.name} ({activeConnection.username})
          </p>
        </div>
        <Button variant="secondary" onClick={() => refetch()} loading={isFetching}>
          전체 재점검
        </Button>
      </div>

      {/* 공급자 선택 — ACL 분기 기준 (프로파일 기본값과 연동) */}
      <label className="flex items-center gap-3 text-sm">
        <span className="font-medium">AI 공급자 전제:</span>
        <select
          className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2"
          value={provider}
          onChange={(e) => setProvider(e.target.value as (typeof PROVIDERS)[number])}
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>
              {p}
              {p === "oci" ? " (기본 — ACL 불필요)" : ""}
            </option>
          ))}
        </select>
        <span className="text-xs text-[var(--color-neutral-60)]">← 분기 기준 (외부 공급자만 ACL 점검)</span>
      </label>

      <Panel>
        {isLoading ? (
          <p className="text-sm text-[var(--color-running)]">항목별 점검 실행 중…</p>
        ) : checkError ? (
          <div className="text-sm">
            <p className="font-medium text-[var(--color-danger)]">
              점검 실행 실패: {checkError instanceof ApiError ? checkError.body.message_ko : String(checkError)}
            </p>
            {checkError instanceof ApiError && checkError.body.hint_ko ? (
              <p className="mt-1 text-[var(--color-neutral-70)]">→ {checkError.body.hint_ko}</p>
            ) : null}
            <Button variant="secondary" className="mt-2" onClick={() => refetch()}>
              재시도
            </Button>
          </div>
        ) : result ? (
          <ul className="flex flex-col divide-y divide-[var(--color-neutral-30)]">
            {result.checks.map((check) => {
              const meta = STATUS_BADGE[check.status];
              const isCredential = check.check_id === "credential";
              return (
                <li key={check.check_id} className="flex flex-col gap-2 py-4">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={meta.badge}>
                      {check.status === "pass" ? "✓" : check.status === "fail" ? "✗" : "◌"} {meta.label}
                    </StatusBadge>
                    <span className="font-semibold">{check.title_ko}</span>
                    {check.docs_ref ? (
                      <span className="text-xs text-[var(--color-info)]">({check.docs_ref})</span>
                    ) : null}
                  </div>
                  <p className="pl-1 text-sm text-[var(--color-neutral-70)]">{check.description_ko}</p>

                  {/* 근거 SQL 접기 */}
                  {check.evidence_sql ? (
                    <SqlBlock label="근거 SQL 보기" sql={check.evidence_sql} />
                  ) : null}

                  {/* Data Access — 상시 거버넌스 토글 (앱은 DB 실제 상태를 읽을 수 없어 강제 적용 제공) */}
                  {check.check_id === "data_access" ? (
                    <div className="flex flex-col gap-2 rounded-[var(--radius-md)] bg-[var(--color-neutral-10)] p-3">
                      <p className="text-xs text-[var(--color-neutral-60)]">
                        ⓘ 표시 상태는 앱이 기록한 추정값이며 DB 실제 상태와 다를 수 있습니다. narrate/합성
                        데이터가 ORA-20000으로 막히면 아래 [활성화]로 ENABLE_DATA_ACCESS를 직접 실행하세요.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          loading={applyMutation.isPending}
                          onClick={() =>
                            applyMutation.mutate([{ check_id: "data_access", enable: true }])
                          }
                        >
                          활성화 (ENABLE)
                        </Button>
                        <Button
                          variant="secondary"
                          loading={applyMutation.isPending}
                          onClick={() =>
                            applyMutation.mutate([{ check_id: "data_access", enable: false }])
                          }
                        >
                          비활성화 (DISABLE)
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  {/* 미충족 항목 — fix_sql 전문 미리보기(필수) + 원클릭 적용 (data_access는 위 토글로 처리) */}
                  {check.status !== "pass" && check.fix_sql && check.check_id !== "data_access" ? (
                    <div className="flex flex-col gap-2 rounded-[var(--radius-md)] bg-[var(--color-neutral-10)] p-3">
                      {check.check_id === "resource_principal" ? (
                        <p className="text-xs text-[var(--color-neutral-60)]">
                          방법 A: Resource Principal <StatusBadge status="info">권장 — 키 관리 불필요</StatusBadge>{" "}
                          ⚠ 사전 조건: 테넌시 Dynamic Group + IAM 정책
                        </p>
                      ) : null}
                      <SqlBlock preview label="실행될 SQL 보기" sql={check.fix_sql} defaultOpen />

                      {/* credential — API 서명 키 폼 (방법 B 폴백) */}
                      {isCredential ? (
                        <div>
                          <button
                            className="text-sm text-[var(--color-link)] underline"
                            onClick={() => setCredFormOpen((v) => !v)}
                          >
                            방법 B: API 서명 키(User Principal) credential 폼{" "}
                            {credFormOpen ? "닫기 ▴" : "열기 ▾"}
                          </button>
                          {credFormOpen ? (
                            <>
                              {ociDefaults?.available ? (
                                <div className="mt-2 flex flex-wrap items-center gap-2 rounded-[var(--radius-sm)] bg-[var(--color-info-tint)] p-2 text-xs">
                                  <StatusBadge status="info">~/.oci 기본값 적용됨</StatusBadge>
                                  <span className="text-[var(--color-neutral-70)]">
                                    config·api-key.pem에서 user/tenancy/fingerprint/private_key를 채웠습니다.
                                  </span>
                                  <button
                                    className="text-[var(--color-link)] underline"
                                    onClick={() => applyOciDefaults(ociDefaults)}
                                  >
                                    다시 채우기
                                  </button>
                                </div>
                              ) : (
                                <p className="mt-2 text-xs text-[var(--color-neutral-60)]">
                                  ~/.oci/config가 없어 기본값을 채우지 않았습니다. 직접 입력하세요.
                                </p>
                              )}
                            <div className="mt-2 grid grid-cols-2 gap-3">
                              <Field
                                id="cred-name"
                                label="credential_name"
                                value={cred.credential_name}
                                onChange={(e) => setCred({ ...cred, credential_name: e.target.value })}
                              />
                              <Field
                                id="cred-fingerprint"
                                label="fingerprint"
                                value={cred.fingerprint ?? ""}
                                onChange={(e) => setCred({ ...cred, fingerprint: e.target.value })}
                              />
                              <Field
                                id="cred-user"
                                label="user_ocid"
                                value={cred.user_ocid ?? ""}
                                onChange={(e) => setCred({ ...cred, user_ocid: e.target.value })}
                              />
                              <Field
                                id="cred-tenancy"
                                label="tenancy_ocid"
                                value={cred.tenancy_ocid ?? ""}
                                onChange={(e) => setCred({ ...cred, tenancy_ocid: e.target.value })}
                              />
                              <div className="col-span-2 flex flex-col gap-1">
                                <label htmlFor="cred-key" className="text-sm font-medium">
                                  private_key
                                </label>
                                <textarea
                                  id="cred-key"
                                  rows={4}
                                  className="rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] p-2 font-mono text-xs"
                                  value={cred.private_key ?? ""}
                                  onChange={(e) => setCred({ ...cred, private_key: e.target.value })}
                                  placeholder="-----BEGIN PRIVATE KEY-----"
                                />
                                <p className="text-xs text-[var(--color-neutral-60)]">
                                  비밀값은 응답·로그에 ***MASKED***로만 표시됩니다.
                                </p>
                              </div>
                            </div>
                            </>
                          ) : null}
                        </div>
                      ) : null}

                      <div>
                        <Button
                          onClick={() => applyMutation.mutate([toApplyItem(check)])}
                          loading={applyMutation.isPending}
                        >
                          적용
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  {/* 통과 항목 중 제거 가능(resource_principal / credential) — 해제 미리보기 + 제거 */}
                  {check.status === "pass" && check.remove_sql ? (
                    <div className="flex flex-col gap-2 rounded-[var(--radius-md)] border border-[var(--color-danger-tint)] bg-[var(--color-neutral-0)] p-3">
                      <p className="text-xs text-[var(--color-neutral-60)]">
                        이 인증은 이미 설정되어 있습니다. 데모 정리/전환을 위해 제거할 수 있습니다.
                        {check.check_id === "credential"
                          ? ` (대상: ${cred.credential_name})`
                          : ""}
                      </p>
                      <SqlBlock preview label="제거 시 실행될 SQL 보기" sql={check.remove_sql} />
                      <div>
                        <Button
                          variant="danger"
                          onClick={() => removeItem(check)}
                          loading={applyMutation.isPending}
                        >
                          {check.check_id === "resource_principal"
                            ? "Resource Principal 해제"
                            : "User Principal(credential) 제거"}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : null}
      </Panel>

      {/* 적용 결과/오류 */}
      {applyMutation.data ? (
        <Panel variant="explain" title="적용 결과 (자동 재점검 반영됨)">
          <ul className="flex flex-col gap-2">
            {applyMutation.data.applied.map((a) => (
              <li key={a.check_id} className="text-sm">
                <StatusBadge status={a.ok ? "success" : "error"}>
                  {a.ok ? "✓ 성공" : "✗ 실패"}
                </StatusBadge>{" "}
                <code>{a.check_id}</code>
                {a.error ? <span className="ml-2 text-[var(--color-danger)]">{a.error.message_ko}</span> : null}
                <SqlBlock label="실행된 SQL 보기" sql={a.executed_sql} />
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
      {applyError ? (
        <Panel variant="explain">
          <p className="text-sm font-medium text-[var(--color-danger)]">{applyError.message_ko}</p>
          {applyError.hint_ko ? (
            <p className="mt-1 text-sm text-[var(--color-neutral-70)]">→ {applyError.hint_ko}</p>
          ) : null}
        </Panel>
      ) : null}

      {/* 하단 진행 요약 + CTA */}
      {result ? (
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium">
            진행: {passCount}/{applicableCount} 통과
          </span>
          {failedChecks.length > 0 ? (
            <Button
              variant="secondary"
              onClick={() => applyMutation.mutate(failedChecks.map(toApplyItem))}
              loading={applyMutation.isPending}
            >
              미충족 항목 모두 적용 ({failedChecks.length}건)
            </Button>
          ) : null}
          {/* 가드 레일은 잠금이 아닌 경고 — 미통과여도 진입 허용 (design.md §1.2) */}
          <Button onClick={() => navigate("/profiles")}>다음: 프로파일 →</Button>
          {result.overall !== "pass" ? (
            <span className="text-xs text-[var(--color-warning)]">
              미충족 항목이 남아 있습니다 — 데모 중 오류가 발생할 수 있습니다.
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default Permissions;
