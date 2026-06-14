/**
 * Feedback 페이지 — 시연하기 (플레이그라운드 다음) / FR-06 보강.
 * Select AI 피드백: 생성 SQL에 긍정/부정 피드백(교정)을 주고, 같은 질문 재실행으로 개선 비교.
 * 권한: 정밀(sql_id, 마지막 AI SQL) 경로는 SYS.V_$MAPPED_SQL/V_$SESSION READ 권한이 필요.
 *   권한 부재 시 안내 + [권한 부여], 부여 권한이 없으면 불가 사유 표시.
 * 근거: selectai-reference §14(FEEDBACK), api-spec §5.3.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, getEnvelope, postEnvelope } from "../api/client";
import type { GenerateResult, ProfileSummary } from "../api/types";
import Button from "../components/Button";
import ComparePanes from "../components/ComparePanes";
import ResultGrid from "../components/ResultGrid";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";
import { useConnectionStore } from "../store/connectionStore";

interface FeedbackPriv {
  current_user: string;
  required: string[];
  held: string[];
  missing: string[];
  has_feedback_grants: boolean;
  can_grant_all: boolean;
  grant_sql: string[];
  blocked_reason_ko: string | null;
}

/** 피드백 벡터 테이블에 저장된 한 건 (검증용) */
interface FeedbackItem {
  prompt: string | null;
  sql_text: string | null;
  sql_id: string | null;
  feedback_type: string | null;
  response: string | null;
  feedback_content: string | null;
}
interface FeedbackList {
  profile_name: string;
  table: string;
  exists: boolean;
  items: FeedbackItem[];
}
/** POST /selectai/feedback 응답 — 방금 저장된 행(stored) 동봉 */
interface FeedbackSendResult {
  ok: boolean;
  feedback_type: string;
  operation: string;
  stored: FeedbackItem | null;
}

/** runsql 결과 렌더 — 생성된 SQL + 결과 표 */
function ResultView({ result }: { result: GenerateResult }) {
  return (
    <div className="flex flex-col gap-2">
      {result.generated_sql ? (
        <SqlBlock defaultOpen label="생성된 SQL" sql={result.generated_sql} />
      ) : null}
      {result.columns && result.rows ? (
        <ResultGrid
          columns={result.columns}
          rows={result.rows}
          truncated={result.truncated ?? undefined}
        />
      ) : result.response_text ? (
        <p className="whitespace-pre-wrap text-sm">{result.response_text}</p>
      ) : null}
    </div>
  );
}

export function Feedback() {
  const activeConnection = useConnectionStore((s) => s.activeConnection);
  const pushToast = useToastStore((s) => s.push);

  const [profile, setProfile] = useState("");
  const [question, setQuestion] = useState("총 시청 횟수는 얼마인가요?");
  const [feedbackContent, setFeedbackContent] = useState("");
  const [responseSql, setResponseSql] = useState("");
  const [before, setBefore] = useState<GenerateResult | null>(null);
  const [after, setAfter] = useState<GenerateResult | null>(null);

  const tag = (a: string) => `PG-feedback/${a}`;

  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });
  const profiles = profilesQuery.data ?? [];

  // 피드백 권한 점검
  const privQuery = useQuery({
    queryKey: ["feedback", "priv"],
    queryFn: async () =>
      (await getEnvelope<FeedbackPriv>("/selectai/feedback/privilege-check", undefined, {
        suppressErrorToast: true,
      })).data,
    enabled: !!activeConnection,
  });
  const priv = privQuery.data;

  const grantMut = useMutation({
    mutationFn: () =>
      postEnvelope<{ summary: { done: number; failed: number }; results: { object: string; ok: boolean; error?: string }[] }>(
        "/selectai/feedback/grant",
        {},
        { sqlLogTag: tag("권한부여") },
      ),
    onSuccess: (env) => {
      const s = env.data.summary;
      const err = env.data.results.find((r) => !r.ok)?.error;
      pushToast({
        status: s.failed > 0 ? "warning" : "success",
        title: `피드백 권한 부여 — 성공 ${s.done}, 실패 ${s.failed}`,
        body: s.failed > 0 ? err : undefined,
      });
      void privQuery.refetch();
    },
  });

  const profileName = profile || null;
  // 실제 사용 프로파일 — 선택값 우선, 없으면 기본 프로파일
  const defaultProfile = profiles.find((p) => p.is_default)?.profile_name ?? "";
  const effectiveProfile = profile || defaultProfile;

  // 저장된 피드백 조회(검증) — 프로파일의 피드백 벡터 테이블 내용을 직접 출력
  const feedbackListQuery = useQuery({
    queryKey: ["feedback", "list", effectiveProfile],
    enabled: !!activeConnection && !!effectiveProfile,
    queryFn: async () =>
      (
        await getEnvelope<FeedbackList>(
          `/selectai/feedback/list?profile_name=${encodeURIComponent(effectiveProfile)}`,
          undefined,
          { suppressErrorToast: true },
        )
      ).data,
  });
  const feedbackList = feedbackListQuery.data;

  // 저장된 피드백 개별 삭제 — DBMS_CLOUD_AI.FEEDBACK(operation=>'delete')
  const deleteFeedback = useMutation({
    mutationFn: (item: FeedbackItem) =>
      postEnvelope(
        "/selectai/feedback",
        {
          profile_name: effectiveProfile,
          // sql_text가 있으면 그 경로로 삭제(검증됨), 없으면 sql_id 경로
          sql_text: item.sql_text ?? null,
          sql_id: item.sql_text ? null : item.sql_id,
          feedback_type: (item.feedback_type as "positive" | "negative") || "positive",
          operation: "delete",
        },
        { sqlLogTag: tag("feedback:delete") },
      ),
    onSuccess: () => {
      pushToast({ status: "success", title: "피드백 1건 삭제됨" });
      void feedbackListQuery.refetch();
    },
  });

  // 1) SQL 생성+실행 (runsql)
  const genBefore = useMutation({
    mutationFn: () =>
      postEnvelope<GenerateResult>("/selectai/generate", {
        prompt: question,
        action: "runsql",
        profile_name: profileName,
        row_limit: 100,
      }, { sqlLogTag: tag("runsql-전") }),
    onSuccess: (env) => {
      setBefore(env.data);
      setAfter(null);
      // 교정 입력란에 생성 SQL을 미리 채움 — 부정+교정 시 ORDER BY 등만 덧붙이면 됨
      setResponseSql(env.data.generated_sql ?? "");
    },
  });

  // 2) 피드백 적용 (sql_text 경로 — 권한 불필요)
  const sendFeedback = useMutation({
    mutationFn: (vars: { feedback_type: "positive" | "negative" }) =>
      postEnvelope<FeedbackSendResult>("/selectai/feedback", {
        profile_name: effectiveProfile,
        sql_text: question,
        feedback_type: vars.feedback_type,
        response: responseSql.trim() || null,
        feedback_content: feedbackContent.trim() || null,
        operation: "add",
      }, { sqlLogTag: tag(`feedback:${vars.feedback_type}`) }),
    onSuccess: (env, vars) => {
      const stored = env.data.stored;
      pushToast({
        status: stored ? "success" : "warning",
        title: `피드백(${vars.feedback_type === "positive" ? "긍정" : "부정"}) ${
          stored ? "저장 확인됨" : "전달됨(저장 확인 실패)"
        }`,
        body: stored
          ? `피드백 테이블에 기록됨 — 아래 '저장된 피드백'에서 확인하세요.`
          : "목록 조회로 확인하세요.",
      });
      // 저장 내용 즉시 갱신 — 명시적 검증
      void feedbackListQuery.refetch();
    },
  });

  // 3) 같은 질문 재실행 (runsql) — before/after 비교
  const genAfter = useMutation({
    mutationFn: () =>
      postEnvelope<GenerateResult>("/selectai/generate", {
        prompt: question,
        action: "runsql",
        profile_name: profileName,
        row_limit: 100,
      }, { sqlLogTag: tag("runsql-후") }),
    onSuccess: (env) => setAfter(env.data),
  });

  if (!activeConnection) {
    return (
      <Panel title="피드백">
        <p className="text-sm text-[var(--color-neutral-60)]">
          먼저 커넥션을 연결하세요.{" "}
          <Link to="/connections" className="text-[var(--color-link)] underline">
            ① 커넥션으로 이동
          </Link>
        </p>
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-bold">Select AI 피드백</h2>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          생성된 SQL에 긍정/부정 피드백(교정)을 주면 이후 유사 질문의 NL2SQL 정확도가 개선됩니다 (26ai
          전용, NL2SQL 프로파일). 같은 질문을 다시 실행해 전/후를 비교하세요.
        </p>
      </div>

      {/* 권한 점검 배너 */}
      <Panel title="피드백 권한">
        {privQuery.isFetching && !priv ? (
          <p className="text-sm text-[var(--color-running)]">권한 점검 중…</p>
        ) : priv ? (
          priv.has_feedback_grants ? (
            <div className="flex items-center gap-2">
              <StatusBadge status="success">권한 보유</StatusBadge>
              <span className="text-xs text-[var(--color-neutral-60)]">
                {priv.current_user} — {priv.held.join(", ")} READ (정밀 sql_id 피드백 가능)
              </span>
            </div>
          ) : (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-warning)] bg-[var(--color-warning-tint)] p-3">
              <div className="flex items-center gap-2">
                <StatusBadge status="warning">권한 부재</StatusBadge>
                <span className="text-sm font-medium">
                  누락: {priv.missing.join(", ")} READ
                </span>
              </div>
              <p className="mt-1 text-sm text-[var(--color-neutral-70)]">
                정밀 피드백(마지막 AI SQL, sql_id 경로)에는 SYS.V_$MAPPED_SQL / V_$SESSION READ 권한이
                필요합니다. (아래 sql_text 기반 피드백은 권한 없이도 동작합니다.)
              </p>
              {priv.can_grant_all ? (
                <div className="mt-2">
                  <p className="text-xs text-[var(--color-neutral-60)]">
                    실행될 GRANT: {priv.grant_sql.join("; ")}
                  </p>
                  <Button variant="secondary" loading={grantMut.isPending} onClick={() => grantMut.mutate()}>
                    권한 부여
                  </Button>
                </div>
              ) : (
                <p className="mt-2 rounded-[var(--radius-sm)] bg-[var(--color-danger-tint)] p-2 text-xs text-[var(--color-danger)]">
                  ⓧ {priv.blocked_reason_ko}
                </p>
              )}
            </div>
          )
        ) : null}
      </Panel>

      {/* 프로파일 선택 — 피드백 권한 아래 위치 (피드백 대상 프로파일) */}
      <Panel title="프로파일">
        <label className="flex flex-wrap items-center gap-2 text-sm">
          피드백 대상 프로파일
          <select
            className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
          >
            <option value="">
              기본 프로파일{defaultProfile ? ` (${defaultProfile})` : ""}
            </option>
            {profiles.map((p) => (
              <option key={p.profile_name} value={p.profile_name}>
                {p.profile_name}
                {p.is_default ? " · 기본" : ""}
              </option>
            ))}
          </select>
          <span className="text-xs text-[var(--color-neutral-60)]">
            적용 대상: <b>{effectiveProfile || "—"}</b>
          </span>
        </label>
      </Panel>

      {/* 저장된 피드백 (명시적 검증) — 피드백 벡터 테이블 내용을 직접 출력 */}
      <Panel title="저장된 피드백 (적용 검증)">
        <div className="mb-3 flex justify-end">
          <Button
            variant="secondary"
            loading={feedbackListQuery.isFetching}
            onClick={() => feedbackListQuery.refetch()}
          >
            새로고침
          </Button>
        </div>
        {!effectiveProfile ? (
          <p className="text-sm text-[var(--color-neutral-60)]">프로파일을 먼저 선택하세요.</p>
        ) : feedbackList == null ? (
          <p className="text-sm text-[var(--color-neutral-60)]">불러오는 중…</p>
        ) : !feedbackList.exists || feedbackList.items.length === 0 ? (
          <p className="text-sm text-[var(--color-neutral-60)]">
            저장된 피드백이 없습니다. 위에서 긍정/부정 피드백을 제출하면 여기에 기록됩니다.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-[var(--color-neutral-60)]">
              프로파일 <b>{feedbackList.profile_name}</b> 의 피드백 테이블{" "}
              <code className="font-mono">{feedbackList.table}</code> 에 저장된{" "}
              <b>{feedbackList.items.length}</b>건 — Select AI가 향후 SQL 생성 시 참조합니다.
            </p>
            <ul className="flex flex-col gap-3">
              {feedbackList.items.map((it, i) => (
                <li
                  key={`${it.sql_id ?? "noid"}-${i}`}
                  className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-3"
                >
                  <div className="mb-1 flex items-center gap-2">
                    <StatusBadge status={it.feedback_type === "positive" ? "success" : "warning"}>
                      {it.feedback_type === "positive" ? "👍 긍정" : "👎 부정"}
                    </StatusBadge>
                    <span className="flex-1 text-sm font-medium">
                      {it.prompt ?? it.sql_text}
                    </span>
                    {it.sql_id ? (
                      <span className="font-mono text-xs text-[var(--color-neutral-50)]">
                        sql_id {it.sql_id}
                      </span>
                    ) : null}
                    <Button
                      variant="danger"
                      loading={
                        deleteFeedback.isPending &&
                        deleteFeedback.variables?.sql_text === it.sql_text &&
                        deleteFeedback.variables?.sql_id === it.sql_id
                      }
                      onClick={() => {
                        if (window.confirm("이 피드백을 삭제할까요?")) deleteFeedback.mutate(it);
                      }}
                      aria-label="피드백 삭제"
                    >
                      <Trash2 size={14} aria-hidden />
                      삭제
                    </Button>
                  </div>
                  {it.feedback_content ? (
                    <p className="mb-2 text-sm text-[var(--color-neutral-70)]">
                      개선 힌트: {it.feedback_content}
                    </p>
                  ) : null}
                  {it.response ? (
                    <SqlBlock defaultOpen label="기록된 SQL (response)" sql={it.response} />
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Panel>


      {/* 피드백 데모 흐름 */}
      <Panel title="① 질문 → SQL 생성+실행 (runsql)">
        <div className="flex flex-wrap items-end gap-3">
          <input
            className="h-9 min-w-80 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="자연어 질문"
          />
          <Button loading={genBefore.isPending} disabled={!question.trim()} onClick={() => genBefore.mutate()}>
            SQL 생성+실행
          </Button>
        </div>
        {genBefore.error instanceof ApiError ? (
          <p className="mt-2 text-sm text-[var(--color-danger)]">{genBefore.error.body.message_ko}</p>
        ) : null}
        {before != null ? (
          <div className="mt-3">
            <p className="mb-1 text-sm font-semibold">실행 결과 (피드백 전)</p>
            <ResultView result={before} />
          </div>
        ) : null}
      </Panel>

      {/* 피드백 */}
      {before != null ? (
        <Panel title="② 피드백 (교정)">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium">개선 힌트 (feedback_content)</label>
            <textarea
              className="w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] p-2 text-sm"
              rows={2}
              placeholder="예: 국가명 기준으로 정렬해주세요"
              value={feedbackContent}
              onChange={(e) => setFeedbackContent(e.target.value)}
            />
            <label className="text-sm font-medium">
              올바른 SQL 전문 (response) — <b>부정+교정</b>의 핵심
            </label>
            <textarea
              className="w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] p-2 font-mono text-xs"
              rows={4}
              placeholder='교정할 SQL 전문 (예: ... ORDER BY c."COUNTRY_NAME")'
              value={responseSql}
              onChange={(e) => setResponseSql(e.target.value)}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="secondary"
                loading={sendFeedback.isPending && sendFeedback.variables?.feedback_type === "positive"}
                onClick={() => sendFeedback.mutate({ feedback_type: "positive" })}
              >
                👍 긍정 (현재 SQL이 정답)
              </Button>
              <Button
                loading={sendFeedback.isPending && sendFeedback.variables?.feedback_type === "negative"}
                disabled={!responseSql.trim()}
                onClick={() => sendFeedback.mutate({ feedback_type: "negative" })}
              >
                👎 부정 + 교정 SQL 학습
              </Button>
              {!responseSql.trim() ? (
                <span className="text-xs text-[var(--color-neutral-50)]">
                  교정하려면 위 SQL을 수정하세요 (예: ORDER BY 추가)
                </span>
              ) : null}
            </div>
            <div className="rounded-[var(--radius-md)] bg-[var(--color-info-tint)] p-3 text-xs text-[var(--color-neutral-70)]">
              <p>
                <b>👍 긍정</b>: 생성된 SQL이 정답이라고 강화합니다 — 같은 질문을 다시 실행해도{" "}
                <b>SQL은 그대로</b>입니다(정상).
              </p>
              <p className="mt-1">
                <b>👎 부정 + 교정</b>: 위 <b>올바른 SQL 전문</b>을 학습시킵니다 — 같은 질문 재실행 시
                교정한 SQL(예: ORDER BY)이 <b>반영됩니다</b>. 쿼리를 바꾸려면 이 버튼을 쓰세요.
              </p>
              <p className="mt-1 text-[var(--color-neutral-50)]">
                ⓘ 프롬프트는 <code>select ai showsql &lt;프롬프트&gt;</code> 형식으로 변환해
                DBMS_CLOUD_AI.FEEDBACK을 호출합니다 (권한 불필요).
              </p>
            </div>
          </div>
        </Panel>
      ) : null}

      {/* ③ 재실행 + 비교 */}
      {sendFeedback.isSuccess ? (
        <Panel title="③ 같은 질문 재실행 → 전/후 비교">
          <Button loading={genAfter.isPending} onClick={() => genAfter.mutate()}>
            같은 질문 다시 실행
          </Button>
          {after != null ? (
            <div className="mt-3">
              {/* 각 박스 안에 '생성 SQL + 데이터 결과'를 함께 담아 전/후를 좌우 비교 */}
              <ComparePanes
                beforeTitle="피드백 전 결과"
                afterTitle="피드백 후 결과"
                before={
                  <div className="flex flex-col gap-2">
                    <SqlBlock
                      defaultOpen
                      label="피드백 전 생성 SQL"
                      sql={before?.generated_sql ?? "—"}
                    />
                    {before?.columns && before.rows ? (
                      <ResultGrid
                        columns={before.columns}
                        rows={before.rows}
                        truncated={before.truncated ?? undefined}
                      />
                    ) : (
                      <span>—</span>
                    )}
                  </div>
                }
                after={
                  <div className="flex flex-col gap-2">
                    <SqlBlock
                      defaultOpen
                      label="피드백 후 생성 SQL"
                      sql={after.generated_sql ?? "—"}
                    />
                    {after.columns && after.rows ? (
                      <ResultGrid
                        columns={after.columns}
                        rows={after.rows}
                        truncated={after.truncated ?? undefined}
                      />
                    ) : (
                      <span>—</span>
                    )}
                  </div>
                }
                summary="각 박스 안에서 생성 SQL과 데이터 결과를 함께 전/후로 비교하세요. (효과는 벡터 유사도 기반이라 항상 즉시 반영되진 않을 수 있습니다.)"
              />
            </div>
          ) : null}
        </Panel>
      ) : null}
    </div>
  );
}

export default Feedback;
