/**
 * Profiles 페이지 — PG-03 (/profiles) / FR-05.
 * 프로파일 목록(USER_CLOUD_AI_PROFILES 뷰 기반) — ★ 기본 프로파일 클릭 변경
 * (PUT /settings/default-profile — 앱 설정, DB 호출 없음 — design.md 설계 전제 3),
 * 삭제는 DROP_PROFILE 미리보기 + 확인 다이얼로그 2단계 (인터랙션 원칙 5).
 * 설계 근거: design.md PG-03, api-spec §4.4·§4.7·§4.8.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, deleteEnvelope, getEnvelope, putEnvelope } from "../api/client";
import type { ProfileSummary } from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

/** DROP_PROFILE 미리보기 문자열 — 표시용 (실제 실행은 백엔드 바인드 변수, api-spec §4.7) */
function dropPreviewSql(profileName: string): string {
  // 표시 시 작은따옴표 이스케이프 (api-spec §1.6)
  return `BEGIN DBMS_CLOUD_AI.DROP_PROFILE('${profileName.replace(/'/g, "''")}'); END;`;
}

export function Profiles() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setDefaultProfileName = useConnectionStore((s) => s.setDefaultProfileName);

  // 삭제 확인 다이얼로그 대상 (null = 닫힘)
  const [deleteTarget, setDeleteTarget] = useState<ProfileSummary | null>(null);

  const { data: profiles, isLoading, error } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });

  // ★ 클릭 = 앱 설정 변경 (DB 호출 없음)
  const setDefaultMutation = useMutation({
    mutationFn: async (profileName: string) =>
      putEnvelope("/settings/default-profile", { profile_name: profileName }),
    onSuccess: (_res, profileName) => {
      setDefaultProfileName(profileName);
      void queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (profileName: string) =>
      deleteEnvelope<{ dropped: boolean; default_cleared?: boolean }>(
        `/profiles/${encodeURIComponent(profileName)}`,
      ),
    onSuccess: (res) => {
      // 기본 프로파일이었다면 앱 설정도 해제됨 (api-spec §4.7)
      if (res.data?.default_cleared) setDefaultProfileName(null);
      setDeleteTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });

  const listError = error instanceof ApiError ? error.body : null;
  const deleteError = deleteMutation.error instanceof ApiError ? deleteMutation.error.body : null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">프로파일</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            Select AI는 프로파일이 있어야 동작합니다. ★를 클릭해 기본 프로파일(앱 설정)을 바꿀 수
            있습니다.
          </p>
        </div>
        <Button onClick={() => navigate("/profiles/new")}>+ 새 프로파일</Button>
      </div>

      <Panel>
        {isLoading ? (
          <p className="text-sm text-[var(--color-running)]">프로파일 목록 조회 중…</p>
        ) : listError ? (
          <div className="text-sm">
            <p className="font-medium text-[var(--color-danger)]">{listError.message_ko}</p>
            {listError.hint_ko ? (
              <p className="mt-1 text-[var(--color-neutral-70)]">→ {listError.hint_ko}</p>
            ) : null}
          </div>
        ) : !profiles || profiles.length === 0 ? (
          <div className="text-sm text-[var(--color-neutral-70)]">
            <p className="font-medium">프로파일이 없습니다. Select AI는 프로파일이 있어야 동작합니다.</p>
            {/* 3줄 개념 해설 (design.md PG-03 빈 상태) */}
            <ul className="mt-2 list-disc pl-5 text-[var(--color-neutral-60)]">
              <li>프로파일 = AI 공급자·모델·대상 테이블(object_list)을 묶은 설정 단위입니다.</li>
              <li>모든 GENERATE 호출은 profile_name을 명시 전달합니다 (세션 SET_PROFILE 미사용).</li>
              <li>대상 테이블을 좁힐수록 NL2SQL 정확도가 올라갑니다.</li>
            </ul>
            <Button className="mt-4" onClick={() => navigate("/profiles/new")}>
              + 새 프로파일
            </Button>
          </div>
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--color-neutral-30)]">
            {profiles.map((p) => (
              <li key={p.profile_name} className="flex items-center gap-3 py-4">
                {/* ★ 기본 프로파일 토글 — 클릭으로 변경, DB 호출 없음 */}
                <button
                  aria-label={`${p.profile_name}을 기본 프로파일로 지정`}
                  title="기본 프로파일로 지정 (앱 설정 — DB 호출 없음)"
                  className={`text-xl ${p.is_default ? "text-[var(--color-warning)]" : "text-[var(--color-neutral-40)] hover:text-[var(--color-warning)]"}`}
                  onClick={() => !p.is_default && setDefaultMutation.mutate(p.profile_name)}
                  disabled={setDefaultMutation.isPending}
                >
                  {p.is_default ? "★" : "☆"}
                </button>
                <div className="flex flex-col">
                  <span className="font-semibold">{p.profile_name}</span>
                  <span className="text-xs text-[var(--color-neutral-60)]">
                    {p.provider ?? "-"} · {p.model ?? "-"}
                    {p.is_default ? " · 기본 프로파일(앱 설정)" : ""}
                  </span>
                </div>
                <StatusBadge status={p.status === "ENABLED" ? "success" : "neutral"}>
                  {p.status === "ENABLED" ? "사용 가능" : "비활성"}
                </StatusBadge>
                <span className="ml-auto flex gap-2">
                  <Button variant="secondary" onClick={() => navigate(`/profiles/${encodeURIComponent(p.profile_name)}`)}>
                    상세
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => navigate(`/profiles/${encodeURIComponent(p.profile_name)}/edit`)}
                  >
                    편집
                  </Button>
                  <Button variant="danger" onClick={() => setDeleteTarget(p)}>
                    삭제
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {/* 삭제 확인 — DROP 미리보기 + 확인 (파괴적 작업 2단계, 인터랙션 원칙 5) */}
      {deleteTarget ? (
        <Panel title={`프로파일 '${deleteTarget.profile_name}' 삭제`}>
          <p className="text-sm text-[var(--color-neutral-70)]">
            아래 PL/SQL이 실행됩니다. 이 작업은 되돌릴 수 없습니다.
            {deleteTarget.is_default ? " 기본 프로파일 설정도 함께 해제됩니다." : ""}
          </p>
          <div className="mt-2">
            <SqlBlock preview defaultOpen label="실행될 SQL 보기" sql={dropPreviewSql(deleteTarget.profile_name)} />
          </div>
          {deleteError ? (
            <p className="mt-2 text-sm text-[var(--color-danger)]">
              {deleteError.message_ko}
              {deleteError.hint_ko ? ` — ${deleteError.hint_ko}` : ""}
            </p>
          ) : null}
          <div className="mt-3 flex gap-3">
            <Button
              variant="danger"
              onClick={() => deleteMutation.mutate(deleteTarget.profile_name)}
              loading={deleteMutation.isPending}
            >
              삭제 실행
            </Button>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
              취소
            </Button>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

export default Profiles;
