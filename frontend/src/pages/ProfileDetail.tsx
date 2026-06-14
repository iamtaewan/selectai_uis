/**
 * ProfileDetail 페이지 — PG-03b (/profiles/:name) / FR-05.
 * 프로파일 속성 상세 (읽기 전용) — USER_CLOUD_AI_PROFILE_ATTRIBUTES 뷰 기반
 * (GET /profiles/{name}, api-spec §4.5 — "showparameter" 액션 대체).
 * 화면 상단 학습 메모: "Select AI에는 showparameter 액션이 없습니다" (design.md PG-03b).
 * 속성명/현재값 표 + 행 선택 시 한국어 해설 패널 동기화, [편집] → PG-03a,
 * [기본 프로파일로 지정] = PUT /settings/default-profile (앱 설정 — DB 호출 없음, §4.8).
 */
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, getEnvelope, putEnvelope } from "../api/client";
import type {
  ProfileAttributeOut,
  ProfileDetail as ProfileDetailData,
  ProfileSummary,
} from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

/** §4.5 내부 SQL — 표시용 미리보기 (실제 실행은 백엔드 바인드 변수) */
const ATTRIBUTES_VIEW_SQL = `SELECT attribute_name, attribute_value
  FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES
 WHERE profile_name = :profile_name;`;

export function ProfileDetail() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { name } = useParams<{ name: string }>();
  const profileName = name ?? "";
  const setDefaultProfileName = useConnectionStore((s) => s.setDefaultProfileName);

  // 해설 패널 동기화 대상 속성 (행 클릭/포커스)
  const [selectedAttr, setSelectedAttr] = useState<ProfileAttributeOut | null>(null);

  // 속성 상세 — USER_CLOUD_AI_PROFILE_ATTRIBUTES 뷰 + description_ko 병합 (api-spec §4.5)
  const {
    data: detail,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["profiles", profileName],
    queryFn: async () =>
      (await getEnvelope<ProfileDetailData>(`/profiles/${encodeURIComponent(profileName)}`)).data,
    enabled: !!profileName,
  });

  // is_default는 DB가 아닌 앱 설정 합성값 — 목록 응답(§4.4)에서 조회 (캐시 공유)
  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });
  const isDefault = profiles?.find((p) => p.profile_name === profileName)?.is_default ?? false;

  // ★ 기본 프로파일로 지정 — 앱 설정 변경 (DB 호출 없음, api-spec §4.8)
  const setDefaultMutation = useMutation({
    mutationFn: async () =>
      putEnvelope("/settings/default-profile", { profile_name: profileName }),
    onSuccess: () => {
      setDefaultProfileName(profileName);
      void queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });

  const detailError = error instanceof ApiError ? error.body : null;

  // 현재 저장된 프로파일 정의를 코드로 (이미 만들어진 프로파일의 현재 설정)
  const currentCode = useMemo(() => {
    if (!detail) return null;
    const fmt = (v: string) => {
      const t = v.trim();
      if (t.startsWith("[") || t.startsWith("{")) {
        try {
          return JSON.stringify(JSON.parse(t));
        } catch {
          /* JSON 아니면 문자열로 */
        }
      }
      return JSON.stringify(v);
    };
    const body = detail.attributes
      .filter((a) => a.value != null && a.value !== "")
      .map((a) => `  "${a.name}": ${fmt(a.value as string)}`)
      .join(",\n");
    return `-- 현재 저장된 프로파일: ${detail.profile_name} (상태: ${detail.status})\n{\n${body}\n}`;
  }, [detail]);

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 — 이름/상태 + 액션 */}
      <div className="flex items-center justify-between">
        <div>
          <button
            className="text-sm text-[var(--color-link)] underline"
            onClick={() => navigate("/profiles")}
          >
            ← 프로파일 목록
          </button>
          <h2 className="mt-1 flex items-center gap-3 text-2xl font-bold">
            {profileName}
            {detail ? (
              <StatusBadge status={detail.status === "ENABLED" ? "success" : "neutral"}>
                {detail.status === "ENABLED" ? "사용 가능" : "비활성"}
              </StatusBadge>
            ) : null}
            {isDefault ? <StatusBadge status="info">★ 기본 프로파일(앱 설정)</StatusBadge> : null}
          </h2>
        </div>
        <div className="flex gap-2">
          {!isDefault ? (
            <Button
              variant="secondary"
              onClick={() => setDefaultMutation.mutate()}
              loading={setDefaultMutation.isPending}
              title="앱 설정 변경 — DB 호출 없음 (SET_PROFILE 미사용)"
            >
              ★ 기본 프로파일로 지정
            </Button>
          ) : null}
          <Button onClick={() => navigate(`/profiles/${encodeURIComponent(profileName)}/edit`)}>
            편집
          </Button>
        </div>
      </div>

      {/* 현재 프로파일 코드 — 이미 만들어진 프로파일의 저장된 설정을 코드로 표시 */}
      {currentCode ? (
        <Panel title="▣ 현재 프로파일 코드 (저장된 설정)">
          <SqlBlock defaultOpen sql={currentCode} label="현재 프로파일의 저장된 속성 코드" />
        </Panel>
      ) : null}

      {/* 학습 메모 — showparameter 액션은 존재하지 않음 (design.md PG-03b / 레퍼런스 §1) */}
      <Panel variant="explain" title="▣ 학습 메모">
        <p>
          Select AI에는 <code>showparameter</code> 액션이 <strong>존재하지 않습니다</strong>. 프로파일
          속성 조회는 <code>USER_CLOUD_AI_PROFILE_ATTRIBUTES</code> 뷰를 사용합니다 — 이 화면이 바로 그
          조회 결과입니다.
        </p>
        <div className="mt-2">
          <SqlBlock label="이 화면이 사용하는 조회 SQL 보기" sql={ATTRIBUTES_VIEW_SQL} />
        </div>
      </Panel>

      <div className="grid grid-cols-[60%_40%] gap-6">
        {/* 좌: 속성명/현재값 표 (읽기 전용) */}
        <Panel title="속성 목록">
          {isLoading ? (
            <p className="text-sm text-[var(--color-running)]">속성 조회 중…</p>
          ) : detailError ? (
            <div className="text-sm">
              <p className="font-medium text-[var(--color-danger)]">{detailError.message_ko}</p>
              {detailError.hint_ko ? (
                <p className="mt-1 text-[var(--color-neutral-70)]">→ {detailError.hint_ko}</p>
              ) : null}
            </div>
          ) : !detail || detail.attributes.length === 0 ? (
            <p className="text-sm text-[var(--color-neutral-60)]">표시할 속성이 없습니다.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[var(--color-neutral-60)]">
                  <th className="border-b border-[var(--color-neutral-40)] px-2 py-2">속성명</th>
                  <th className="border-b border-[var(--color-neutral-40)] px-2 py-2">현재값</th>
                  <th className="border-b border-[var(--color-neutral-40)] px-2 py-2">검증</th>
                </tr>
              </thead>
              <tbody>
                {detail.attributes.map((attr) => {
                  const selected = selectedAttr?.name === attr.name;
                  return (
                    <tr
                      key={attr.name}
                      tabIndex={0}
                      onClick={() => setSelectedAttr(attr)}
                      onFocus={() => setSelectedAttr(attr)}
                      className={`cursor-pointer ${
                        selected
                          ? "bg-[var(--color-info-tint)]"
                          : "hover:bg-[var(--color-neutral-10)]"
                      }`}
                    >
                      <td className="border-b border-[var(--color-neutral-30)] px-2 py-2">
                        <code className="font-medium">{attr.name}</code>
                      </td>
                      <td className="border-b border-[var(--color-neutral-30)] px-2 py-2">
                        {attr.value == null ? (
                          <span className="italic text-[var(--color-neutral-50)]">(null)</span>
                        ) : (
                          <code className="break-all">{attr.value}</code>
                        )}
                      </td>
                      <td className="border-b border-[var(--color-neutral-30)] px-2 py-2">
                        {attr.verified ? (
                          <StatusBadge status="success">검증됨</StatusBadge>
                        ) : (
                          <StatusBadge status="warning">미검증</StatusBadge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>

        {/* 우: 행 선택과 동기화되는 한국어 해설 패널 (PG-03a와 동일 패턴) */}
        <Panel
          variant="explain"
          title={`▣ 속성 해설${selectedAttr ? `: ${selectedAttr.name}` : ""}`}
        >
          {selectedAttr ? (
            <p>
              {selectedAttr.description_ko ??
                "본 가이드에서 미검증 속성입니다. Supplied Package Reference를 확인하세요."}
              {selectedAttr.docs_ref ? (
                <span className="mt-1 block text-xs text-[var(--color-info)]">
                  근거: {selectedAttr.docs_ref}
                </span>
              ) : null}
            </p>
          ) : (
            <p>왼쪽 표에서 속성 행을 클릭하면 한국어 해설과 근거 페이지가 여기에 표시됩니다.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}

export default ProfileDetail;
