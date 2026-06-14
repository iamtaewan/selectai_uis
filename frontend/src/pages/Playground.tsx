/**
 * Playground 페이지 — PG-04 (/playground) / FR-06.
 * Select AI 플레이그라운드 — 같은 자연어 질문을 액션만 바꿔 실행하며 차이를 시연한다.
 * 근거: design.md §3 PG-04, api-spec §5 (selectai/generate·feedback·suggested-prompts·actions).
 * - 액션 탭: runsql/showsql/explainsql/narrate/chat (P0) + showprompt (P1 배지)
 * - 추천 질문 칩: 클릭 = 입력 채움만 (자동 실행 금지 — design.md §5 원칙 5)
 * - 모든 결과 카드 하단에 실제 호출 SQL(envelope.executed_sql) 펼침
 * - 액션 비교 모드: P0 5개 액션 병렬 실행 → 5열 카드
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiError, getEnvelope, postEnvelope } from "../api/client";
import type {
  ActionMeta,
  DefaultProfileSetting,
  Envelope,
  FeedbackRequest,
  GenerateResult,
  ProfileSummary,
  SelectAIAction,
  SuggestedPrompt,
} from "../api/types";
import Button from "../components/Button";
import { useConnectionStore } from "../store/connectionStore";
import Panel from "../components/Panel";
import ResultGrid from "../components/ResultGrid";
import SqlBlock, { highlightSql } from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";

/** 탭에 노출하는 액션 — 5개 (runsql/showsql/explainsql/narrate + showprompt). chat은 챗봇 화면(PG-05) 전용. */
const TAB_ACTIONS: { action: SelectAIAction; p1?: boolean }[] = [
  { action: "runsql" },
  { action: "showsql" },
  { action: "explainsql" },
  { action: "narrate" },
  { action: "showprompt", p1: true },
];

/** 실행 시 동시에 호출하는 전체 액션 (탭 순서와 동일) */
const ALL_ACTIONS: SelectAIAction[] = TAB_ACTIONS.map((t) => t.action);

/** SQL 투명 모드 — localStorage preference (design.md PG-08 X4 결정: 백엔드 API 없음). 키 이름은 합리적 가정 */
function isSqlTransparent(): boolean {
  return localStorage.getItem("selectai.sqlTransparent") !== "off";
}

/** 단일 실행 결과 (성공 envelope 또는 오류) */
interface RunOutcome {
  action: SelectAIAction;
  envelope?: Envelope<GenerateResult>;
  error?: unknown;
}

/** LLM 호출 경과 초 표시용 훅 (design.md §5 원칙 6 — 로딩은 침묵하지 않는다) */
function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(
      () => setSeconds(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [active]);
  return seconds;
}

/** 오류 카드 — ORA 원문은 접고 한국어 원인 + 조치 딥링크 (design.md §4 오류 친화 카드) */
function ErrorCard({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = error instanceof ApiError ? error : null;
  const appCode = apiError?.body.app_code;
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-danger)] bg-[var(--color-danger-tint)] p-4">
      <div className="flex items-center gap-2">
        <StatusBadge status="error">{appCode ?? "오류"}</StatusBadge>
        <p className="font-semibold">
          {appCode === "GENERATED_SQL_INVALID"
            ? "생성된 SQL이 실행되지 않았습니다 — SELECT 외 구문은 자동 차단됩니다"
            : appCode === "DATA_ACCESS_DISABLED"
              ? "Data Access가 비활성입니다 — narrate 액션을 사용할 수 없습니다"
              : (apiError?.body.message_ko ??
                (error instanceof Error ? error.message : "알 수 없는 오류"))}
        </p>
      </div>
      {apiError?.body.hint_ko ? (
        <p className="mt-2 text-sm text-[var(--color-neutral-70)]">{apiError.body.hint_ko}</p>
      ) : null}
      {appCode === "GENERATED_SQL_INVALID" ? (
        <p className="mt-2 text-sm text-[var(--color-neutral-70)]">
          LLM 환각으로 잘못된 구문이 생성될 수 있습니다 — 질문을 더 구체적으로 바꿔 재시도해
          보세요.
        </p>
      ) : null}
      {apiError?.body.detail ? (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[var(--color-link)]">ORA 오류 원문 보기</summary>
          <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs">
            {apiError.body.detail}
          </pre>
        </details>
      ) : null}
      <div className="mt-3 flex gap-2">
        {onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            재시도
          </Button>
        ) : null}
        {appCode === "DATA_ACCESS_DISABLED" ? (
          <Link to="/permissions">
            <Button variant="ghost">권한 점검에서 활성화 →</Button>
          </Link>
        ) : null}
      </div>
    </div>
  );
}

/** 피드백 바 — runsql/showsql 결과 카드의 👍/👎 (api-spec §5.3, P1) */
function FeedbackBar({ prompt, result }: { prompt: string; result: GenerateResult }) {
  const [sent, setSent] = useState<"positive" | "negative" | null>(null);
  const [showNegativeForm, setShowNegativeForm] = useState(false);
  const [feedbackContent, setFeedbackContent] = useState("");

  const feedbackMutation = useMutation({
    mutationFn: (body: FeedbackRequest) => postEnvelope<unknown>("/selectai/feedback", body),
    onSuccess: (_data, body) => {
      setSent(body.feedback_type);
      setShowNegativeForm(false);
    },
  });

  const send = (feedbackType: "positive" | "negative") => {
    feedbackMutation.mutate({
      profile_name: result.profile_name,
      // sql_text에는 자연어 프롬프트 원문을 전달 (api-spec §5.3 예시 패턴)
      sql_text: prompt,
      feedback_type: feedbackType,
      response: result.generated_sql ?? null,
      feedback_content:
        feedbackType === "negative" && feedbackContent ? feedbackContent : null,
      operation: "add",
    });
  };

  if (sent) {
    return (
      <p className="text-sm text-[var(--color-success)]">
        피드백이 DBMS_CLOUD_AI.FEEDBACK으로 전달되었습니다 (
        {sent === "positive" ? "👍 긍정" : "👎 부정"}) — 이후 SQL 생성 정확도에 반영됩니다.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-sm text-[var(--color-neutral-60)]">
        <span>이 SQL이 정확했나요?</span>
        <button
          aria-label="긍정 피드백"
          className="rounded px-2 py-1 hover:bg-[var(--color-neutral-20)]"
          disabled={feedbackMutation.isPending}
          onClick={() => send("positive")}
        >
          👍
        </button>
        <button
          aria-label="부정 피드백"
          className="rounded px-2 py-1 hover:bg-[var(--color-neutral-20)]"
          disabled={feedbackMutation.isPending}
          onClick={() => setShowNegativeForm((v) => !v)}
        >
          👎
        </button>
        <span className="text-xs">(26ai FEEDBACK — feedback_grants 권한 필요)</span>
      </div>
      {showNegativeForm ? (
        <div className="flex gap-2">
          <input
            className="h-9 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3 text-sm"
            placeholder="개선 힌트 (예: married 비교에 UPPER를 사용해 주세요)"
            value={feedbackContent}
            onChange={(e) => setFeedbackContent(e.target.value)}
          />
          <Button
            variant="secondary"
            loading={feedbackMutation.isPending}
            onClick={() => send("negative")}
          >
            보내기
          </Button>
        </div>
      ) : null}
      {feedbackMutation.error ? <ErrorCard error={feedbackMutation.error} /> : null}
    </div>
  );
}

/** 증강 프롬프트 chat 메시지 구조 (OCI GenAI showprompt 출력) */
interface PromptContent {
  type?: string;
  text?: string;
}
interface PromptMessage {
  role?: string;
  content?: PromptContent[] | string;
}

/** 텍스트를 chat 메시지 배열로 파싱 — 형태가 아니면 null */
function parsePromptMessages(text: string): PromptMessage[] | null {
  const t = (text ?? "").trim();
  if (!t.startsWith("[") && !t.startsWith("{")) return null;
  try {
    const parsed: unknown = JSON.parse(t);
    const arr = Array.isArray(parsed) ? parsed : [parsed];
    const ok = arr.every((m) => m && typeof m === "object" && ("content" in m || "role" in m));
    return ok ? (arr as PromptMessage[]) : null;
  } catch {
    return null;
  }
}

/** 메시지의 텍스트 합치기 (content가 배열/문자열 모두 지원) */
function messageText(m: PromptMessage): string {
  if (typeof m.content === "string") return m.content;
  if (Array.isArray(m.content)) {
    return m.content.map((c) => (typeof c === "string" ? c : (c?.text ?? ""))).join("\n");
  }
  return "";
}

/** 이스케이프(\n, \t, \", \\) 복원 — JSON 파싱이 안 되는 원문 폴백용 */
function unescapePrompt(text: string): string {
  return (text ?? "")
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "  ")
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}

/** USER 메시지 — 지시문 + "Question:" 강조 분리 */
function UserPromptBody({ text }: { text: string }) {
  const idx = text.lastIndexOf("Question:");
  const instructions = (idx >= 0 ? text.slice(0, idx) : text).trim();
  const question = idx >= 0 ? text.slice(idx + "Question:".length).trim() : null;
  return (
    <div className="flex flex-col gap-3 p-3">
      {question ? (
        <div className="rounded-[var(--radius-md)] border-l-4 border-[var(--color-brand)] bg-[var(--color-info-tint)] p-3">
          <span className="mr-2 rounded bg-[var(--color-brand)] px-1.5 py-0.5 text-xs font-bold text-[var(--color-neutral-0)]">
            질문
          </span>
          <span className="text-base font-semibold">{question}</span>
        </div>
      ) : null}
      <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-6 text-[var(--color-neutral-80)]">
        {instructions}
      </pre>
    </div>
  );
}

/** 증강 프롬프트(showprompt) 전용 가독성 뷰 — 메시지 구조 분해 + SQL 하이라이트 + 질문 강조 */
function AugmentedPromptView({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const messages = useMemo(() => parsePromptMessages(text), [text]);
  const copyText = useMemo(
    () =>
      messages
        ? messages
            .map((m) => `### ${(m.role ?? "MESSAGE").toUpperCase()}\n${messageText(m)}`)
            .join("\n\n")
        : unescapePrompt(text),
    [messages, text],
  );
  const roleBadge = (role: string) =>
    role === "SYSTEM"
      ? "bg-[var(--color-neutral-70)] text-[var(--color-neutral-0)]"
      : role === "USER"
        ? "bg-[var(--color-brand)] text-[var(--color-neutral-0)]"
        : "bg-[var(--color-neutral-40)] text-[var(--color-neutral-0)]";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 클립보드 불가 — 무시 */
    }
  };

  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)]">
      {/* 헤더 — 설명 + 줄 수 + 복사 */}
      <div className="flex items-center justify-between gap-2 border-b border-[var(--color-neutral-30)] bg-[var(--color-neutral-10)] px-3 py-2">
        <span className="text-sm font-medium">
          LLM에 전송된 증강 프롬프트{" "}
          <span className="text-xs font-normal text-[var(--color-neutral-60)]">
            (스키마 메타데이터 + 지시문 + 질문이 결합된 실제 입력)
          </span>
        </span>
        <button
          className="shrink-0 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 py-1 text-xs hover:bg-[var(--color-neutral-20)]"
          onClick={copy}
        >
          {copied ? "복사됨 ✓" : "복사"}
        </button>
      </div>
      {messages ? (
        <div className="flex flex-col">
          {messages.map((m, i) => {
            const role = (m.role ?? "MESSAGE").toUpperCase();
            const body = messageText(m);
            return (
              <section key={i} className="border-b border-[var(--color-neutral-20)] last:border-b-0">
                <div className="flex items-center gap-2 px-3 py-2">
                  <span className={`rounded px-2 py-0.5 text-xs font-bold ${roleBadge(role)}`}>
                    {role}
                  </span>
                  <span className="text-xs text-[var(--color-neutral-60)]">
                    {role === "SYSTEM" ? "스키마 메타데이터 (테이블/컬럼/관계)" : "지시문 + 질문"}
                  </span>
                </div>
                {role === "SYSTEM" ? (
                  <pre
                    className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs"
                    style={{
                      background: "var(--color-code-bg)",
                      color: "var(--color-code-text)",
                      lineHeight: "var(--leading-code)",
                    }}
                  >
                    <code>{highlightSql(body)}</code>
                  </pre>
                ) : (
                  <UserPromptBody text={body} />
                )}
              </section>
            );
          })}
        </div>
      ) : (
        <div className="max-h-[34rem] overflow-auto bg-[var(--color-neutral-0)] py-2 font-mono text-xs leading-6">
          {unescapePrompt(text)
            .split("\n")
            .map((ln, i) => (
              <div key={i} className="flex hover:bg-[var(--color-neutral-10)]">
                <span className="w-12 shrink-0 select-none pr-3 text-right text-[var(--color-neutral-40)]">
                  {i + 1}
                </span>
                <span className="flex-1 whitespace-pre-wrap break-words pr-3 text-[var(--color-neutral-90)]">
                  {ln || " "}
                </span>
              </div>
            ))}
        </div>
      )}

      {/* 프롬프트 원문 — 펼쳐서 가공 전 원본(JSON 등)을 그대로 확인 */}
      <details className="border-t border-[var(--color-neutral-30)] bg-[var(--color-neutral-10)]">
        <summary className="cursor-pointer px-3 py-2 text-sm text-[var(--color-link)] hover:underline">
          프롬프트 원문 보기 (가공 전 원본)
        </summary>
        <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words bg-[var(--color-neutral-0)] p-3 font-mono text-xs leading-6 text-[var(--color-neutral-80)]">
          {text}
        </pre>
      </details>
    </div>
  );
}

/** 결과 본문 — 액션별 차등 렌더 (runsql=grid / showsql=SQL / explainsql=SQL+설명 / 텍스트) */
function ResultBody({ outcome, prompt }: { outcome: RunOutcome; prompt: string }) {
  const sqlOpen = isSqlTransparent();
  if (outcome.error) return <ErrorCard error={outcome.error} />;
  const envelope = outcome.envelope;
  if (!envelope) return null;
  const result = envelope.data;

  return (
    <div className="flex flex-col gap-3">
      {result.result_type === "table" && result.columns ? (
        <>
          <ResultGrid
            columns={result.columns}
            rows={result.rows ?? []}
            elapsedMs={envelope.elapsed_ms}
            truncated={result.truncated}
          />
          {result.generated_sql ? (
            <SqlBlock
              sql={result.generated_sql}
              label="LLM이 생성한 SQL 보기"
              defaultOpen={sqlOpen}
            />
          ) : null}
        </>
      ) : null}

      {result.result_type === "sql" ? (
        <SqlBlock
          sql={result.generated_sql ?? result.response_text ?? ""}
          label="LLM이 생성한 SQL (실행되지 않음)"
          preview
          defaultOpen
        />
      ) : null}

      {result.result_type === "text" ? (
        <>
          {result.generated_sql ? (
            <SqlBlock sql={result.generated_sql} label="생성된 SQL 보기" defaultOpen={sqlOpen} />
          ) : null}
          {result.action === "showprompt" ? (
            // 증강 프롬프트는 길고 구조적이라 전용 가독성 뷰로 표시
            <AugmentedPromptView text={result.response_text ?? ""} />
          ) : (
            <div className="whitespace-pre-wrap rounded-[var(--radius-lg)] bg-[var(--color-neutral-10)] p-4 text-base leading-relaxed">
              {result.response_text}
            </div>
          )}
        </>
      ) : null}

      {/* 응답 시간 배지 + 프로파일 */}
      <div className="flex items-center gap-3">
        <StatusBadge status="info">⏱ {(envelope.elapsed_ms / 1000).toFixed(1)}s</StatusBadge>
        <StatusBadge status="neutral">{result.profile_name}</StatusBadge>
      </div>
      {(result.action === "runsql" || result.action === "showsql") && result.generated_sql ? (
        <FeedbackBar prompt={prompt} result={result} />
      ) : null}

      {/* 교육적 투명성 — 실제 호출 SQL 전문 (design.md §5 원칙 1) */}
      <SqlBlock
        sql={envelope.executed_sql}
        label="이 결과를 만든 실제 호출 SQL 보기"
        defaultOpen={sqlOpen}
      />
    </div>
  );
}

export function Playground() {
  // 커넥션 의존 쿼리는 활성 커넥션이 있을 때만 발사 — 새로고침 직후 헤더 누락(CONNECTION_REQUIRED) 방지
  const activeConnectionId = useConnectionStore((s) => s.activeConnectionId);
  const [prompt, setPrompt] = useState("");
  const [activeAction, setActiveAction] = useState<SelectAIAction>("runsql");
  const [selectedProfile, setSelectedProfile] = useState<string>(""); // "" = 앱 기본 프로파일 사용
  // 액션별 결과 — [실행] 시 6개 액션을 동시 호출하여 각 탭에 채운다.
  const [results, setResults] = useState<Partial<Record<SelectAIAction, RunOutcome>>>({});
  const [pending, setPending] = useState<Set<SelectAIAction>>(new Set());
  const promptRef = useRef<HTMLInputElement>(null);

  // 메타데이터 조회 (정적 — 캐시 무한)
  const actionsQuery = useQuery({
    queryKey: ["selectai", "actions"],
    queryFn: () => getEnvelope<ActionMeta[]>("/selectai/actions"),
    staleTime: Infinity,
  });
  const suggestedQuery = useQuery({
    queryKey: ["selectai", "suggested-prompts"],
    queryFn: () => getEnvelope<SuggestedPrompt[]>("/selectai/suggested-prompts"),
    staleTime: Infinity,
  });
  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    // 공유 키 ["profiles"] 반환 형태를 배열로 통일. 커넥션 필요 → 활성 시에만 발사
    enabled: !!activeConnectionId,
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });
  const defaultProfileQuery = useQuery({
    queryKey: ["settings", "default-profile"],
    enabled: !!activeConnectionId, // 커넥션 필요 → 활성 시에만 발사 (새로고침 race 방지)
    queryFn: () => getEnvelope<DefaultProfileSetting>("/settings/default-profile"),
  });

  const actionMeta = useMemo(() => {
    const map = new Map<string, ActionMeta>();
    actionsQuery.data?.data.forEach((meta) => map.set(meta.action, meta));
    return map;
  }, [actionsQuery.data]);

  // 단일 액션 호출 (실행/재시도 공용) — 결과를 results[action]에 채우고 pending에서 제거
  const runOne = (action: SelectAIAction) => {
    setPending((p) => new Set(p).add(action));
    setResults((p) => {
      const next = { ...p };
      delete next[action];
      return next;
    });
    postEnvelope<GenerateResult>(
      "/selectai/generate",
      { prompt, action, profile_name: selectedProfile || null, row_limit: 100 },
      { sqlLogTag: `PG-04/${action}` },
    )
      .then((envelope) => setResults((p) => ({ ...p, [action]: { action, envelope } })))
      .catch((error) => setResults((p) => ({ ...p, [action]: { action, error } })))
      .finally(() =>
        setPending((p) => {
          const n = new Set(p);
          n.delete(action);
          return n;
        }),
      );
  };

  // [실행] — 6개 액션을 동시에 시작 (각 탭이 완료되는 대로 독립적으로 채워진다)
  const runAll = () => {
    if (!prompt.trim()) return;
    setResults({});
    setPending(new Set(ALL_ACTIONS));
    ALL_ACTIONS.forEach((action) =>
      postEnvelope<GenerateResult>(
        "/selectai/generate",
        { prompt, action, profile_name: selectedProfile || null, row_limit: 100 },
        { sqlLogTag: `PG-04/${action}` },
      )
        .then((envelope) => setResults((p) => ({ ...p, [action]: { action, envelope } })))
        .catch((error) => setResults((p) => ({ ...p, [action]: { action, error } })))
        .finally(() =>
          setPending((p) => {
            const n = new Set(p);
            n.delete(action);
            return n;
          }),
        ),
    );
  };

  const running = pending.size > 0;
  const elapsedSeconds = useElapsedSeconds(running);
  const canRun = prompt.trim().length > 0 && !running;
  const defaultProfileName = defaultProfileQuery.data?.data.profile_name;
  const activeOutcome = results[activeAction];
  const activePending = pending.has(activeAction);
  const hasRun = running || Object.keys(results).length > 0;

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 — 제목 + 프로파일 선택기 */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Select AI 플레이그라운드</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            [실행]을 누르면 같은 질문을 5개 액션(runsql·showsql·explainsql·narrate·showprompt)으로
            동시에 호출하고, 각 탭에서 결과를 비교합니다.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          프로파일
          <select
            className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2"
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
          >
            <option value="">기본{defaultProfileName ? ` (${defaultProfileName})` : ""}</option>
            {(profilesQuery.data ?? []).map((profile) => (
              <option key={profile.profile_name} value={profile.profile_name}>
                {profile.profile_name}
                {profile.status === "DISABLED" ? " (비활성)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* 질문 입력 + 추천 칩 */}
      <Panel>
        <div className="flex gap-2">
          <input
            ref={promptRef}
            className="h-11 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3 text-base"
            placeholder="자연어로 질문하세요 (예: how many customers in San Francisco are married)"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && canRun) runAll();
            }}
          />
          <Button large loading={running} disabled={!canRun} onClick={runAll}>
            실행 (5개 액션 동시)
          </Button>
        </div>
        {/* 추천 질문 칩 — 클릭 = 입력 채움만, 자동 실행 안 함 (시연자가 말할 시간 확보) */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs text-[var(--color-neutral-60)]">추천 질문:</span>
          {suggestedQuery.data?.data.map((suggestion) => (
            <button
              key={suggestion.prompt}
              className="rounded-full border border-[var(--color-neutral-40)] bg-[var(--color-neutral-10)] px-3 py-1 text-sm hover:bg-[var(--color-neutral-20)]"
              onClick={() => {
                setPrompt(suggestion.prompt);
                setActiveAction(suggestion.recommended_action);
                promptRef.current?.focus();
              }}
              title={`스키마: ${suggestion.schema} / 추천 액션: ${suggestion.recommended_action}`}
            >
              {suggestion.prompt}
            </button>
          ))}
        </div>
      </Panel>

      {/* 액션 탭 — 전환 시 질문 유지, 재실행은 명시 버튼으로 */}
      <div>
        <div className="flex gap-1 border-b border-[var(--color-neutral-30)]">
          {TAB_ACTIONS.map(({ action, p1 }) => {
            // 탭별 상태 표시 — 실행 중(◌) / 완료(✓) / 실패(✗)
            const isPending = pending.has(action);
            const out = results[action];
            const mark = isPending ? "◌" : out?.error ? "✗" : out?.envelope ? "✓" : "";
            const markColor = isPending
              ? "text-[var(--color-running)]"
              : out?.error
                ? "text-[var(--color-danger)]"
                : out?.envelope
                  ? "text-[var(--color-success)]"
                  : "";
            return (
              <button
                key={action}
                className={`flex items-center gap-1 rounded-t-[var(--radius-md)] px-4 py-2 font-mono text-sm ${
                  activeAction === action
                    ? "border border-b-0 border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] font-bold text-[var(--color-brand)]"
                    : "text-[var(--color-neutral-60)] hover:text-[var(--color-neutral-90)]"
                }`}
                onClick={() => setActiveAction(action)}
              >
                {mark ? (
                  <span className={`${markColor} ${isPending ? "animate-pulse" : ""}`}>{mark}</span>
                ) : null}
                {action}
                {p1 ? <StatusBadge status="info">P1</StatusBadge> : null}
              </button>
            );
          })}
        </div>

        <Panel className="rounded-t-none border-t-0">
          {/* 액션 한 줄 한국어 정의 ⓘ (레퍼런스 §1 액션 표 문구) */}
          <p className="mb-4 text-sm text-[var(--color-neutral-60)]">
            ⓘ <span className="font-mono font-semibold">{activeAction}</span> —{" "}
            {actionMeta.get(activeAction)?.title_ko ?? ""}
            {actionMeta.get(activeAction)?.description_ko
              ? ` · ${actionMeta.get(activeAction)?.description_ko}`
              : ""}
          </p>

          {/* 활성 탭 로딩 — 실행 중 SQL 패턴 + 경과 초 */}
          {activePending ? (
            <div className="flex flex-col gap-2 rounded-[var(--radius-lg)] bg-[var(--color-neutral-10)] p-6">
              <p className="font-semibold">
                ◌ {activeAction} 실행 중… {elapsedSeconds}초
                {elapsedSeconds >= 10 ? " — OCI GenAI 응답 대기 중입니다 (정상 범위)" : ""}
              </p>
              <p className="text-xs text-[var(--color-neutral-60)]">
                다른 액션도 동시에 실행 중입니다 — 완료된 탭은 ✓로 표시됩니다.
              </p>
              <SqlBlock
                sql={`SELECT DBMS_CLOUD_AI.GENERATE(\n  prompt       => :prompt,\n  profile_name => :profile_name,\n  action       => :action,\n  params       => :params_json) AS response\nFROM dual;`}
                label="지금 실행 중인 SQL 패턴 보기"
                defaultOpen
              />
            </div>
          ) : null}

          {/* 활성 탭 결과 카드 */}
          {!activePending && activeOutcome ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold">{activeOutcome.action}</span>
                {activeOutcome.error ? (
                  <StatusBadge status="error">실패</StatusBadge>
                ) : (
                  <StatusBadge status="success">완료</StatusBadge>
                )}
              </div>
              <ResultBody outcome={activeOutcome} prompt={prompt} />
              {activeOutcome.error ? (
                <div className="flex flex-col gap-2">
                  <p className="text-sm text-[var(--color-neutral-60)]">
                    💡 질문을 바꿔보세요 — 컬럼/테이블을 더 구체적으로 언급하면 정확도가 올라갑니다.
                  </p>
                  <div>
                    <Button variant="secondary" onClick={() => runOne(activeAction)}>
                      이 액션만 재시도
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {/* 실행했지만 이 탭은 아직 결과 없음 (드문 경우) */}
          {hasRun && !activePending && !activeOutcome ? (
            <p className="text-sm text-[var(--color-neutral-60)]">
              이 탭의 결과가 아직 없습니다. [실행]을 다시 누르거나 탭을 전환해 보세요.
            </p>
          ) : null}

          {/* 빈 상태 — 액션 파이프라인 개념 안내 */}
          {!hasRun ? (
            <div className="rounded-[var(--radius-lg)] bg-[var(--color-neutral-10)] p-8 text-center text-[var(--color-neutral-60)]">
              <p className="text-base">추천 질문을 클릭하거나 직접 입력한 뒤 [실행]을 누르세요.</p>
              <p className="mt-3 font-mono text-sm">
                [실행] → <b>showsql</b>(SQL 생성) · <b>runsql</b>(실행=표) · <b>explainsql</b>(설명) ·{" "}
                <b>narrate</b>(서술) · <b>showprompt</b>(증강 프롬프트)를 동시에
              </p>
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

export default Playground;
