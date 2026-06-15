/**
 * Chat 페이지 — PG-05 (/chat) / FR-07.
 * Conversations 기반 멀티턴 챗봇 — "맥락을 기억하는 데이터 대화" 시연.
 * 근거: design.md §3 PG-05, api-spec §6 (chat/conversations·messages·compare).
 * - 대화 생성: POST /chat/conversations (CREATE_CONVERSATION 함수형 — UUID 반환)
 * - 턴 전송: POST /chat/conversations/{id}/messages — conversation_id는 params JSON으로 전달
 * - 맥락 비교 모드: POST /chat/compare → conversation_id 유/무 좌우 비교 (ComparePanes)
 * - URL ?conversation=<id> 진입 시 해당 대화 자동 선택 (PG-05a [이어가기] 딥링크)
 */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { ApiError, getEnvelope, postEnvelope } from "../api/client";
import type {
  ChatCompareResult,
  ChatMessageOut,
  ConversationAction,
  ConversationCreate,
  ConversationOut,
  DefaultProfileSetting,
  GenerateResult,
  ProfileSummary,
  SuggestedPromptsResult,
} from "../api/types";
import Button from "../components/Button";
import ComparePanes from "../components/ComparePanes";
import SuggestedPrompts from "../components/SuggestedPrompts";
import Panel from "../components/Panel";
import ResultGrid from "../components/ResultGrid";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";

/** 대화 지원 액션 5종 (p47 Note — 그 외는 400 ACTION_NOT_SUPPORTED_IN_CONVERSATION) */
const TURN_ACTIONS: ConversationAction[] = ["narrate", "chat", "runsql", "showsql", "explainsql"];

/** 추천 후속 질문 — 레퍼런스 §9 대화형 시나리오 순서 (total → by country → age group → top 5) */
/** SQL 투명 모드 preference (PG-08 X4 — localStorage, 키 이름은 합리적 가정) */
function isSqlTransparent(): boolean {
  return localStorage.getItem("selectai.sqlTransparent") !== "off";
}

/** 턴 이력 API 응답 형태 (api-spec §6.4) */
interface ConversationMessages {
  conversation_id: string;
  messages: ChatMessageOut[];
}

/** 화면용 턴 — 서버 이력 + 이번 세션 실행 상세(executed_sql/elapsed)를 합친 뷰 모델 */
interface TurnView {
  prompt: string;
  action?: string | null;
  responseText?: string | null;
  /** 이번 세션에서 실행한 턴만 구조화 결과 보유 */
  result?: GenerateResult;
  executedSql?: string[];
  elapsedMs?: number | null;
  error?: unknown;
  pending?: boolean;
}

function errorText(error: unknown): { message: string; hint?: string | null; appCode?: string } {
  if (error instanceof ApiError) {
    return { message: error.body.message_ko, hint: error.body.hint_ko, appCode: error.body.app_code };
  }
  return { message: error instanceof Error ? error.message : "알 수 없는 오류" };
}

/** AI 응답 버블 본문 — runsql이면 표, 그 외 텍스트 */
function TurnResponse({ turn }: { turn: TurnView }) {
  const sqlOpen = isSqlTransparent();
  if (turn.pending) {
    return (
      <p className="animate-pulse text-[var(--color-neutral-60)]">◌ LLM 응답 생성 중…</p>
    );
  }
  if (turn.error) {
    const { message, hint, appCode } = errorText(turn.error);
    return (
      <div className="rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-danger-tint)] p-3 text-sm">
        <StatusBadge status="error">{appCode ?? "턴 실패"}</StatusBadge>
        <p className="mt-1 font-medium">{message}</p>
        {hint ? <p className="mt-1 text-[var(--color-neutral-70)]">{hint}</p> : null}
        {appCode === "DATA_ACCESS_DISABLED" ? (
          <Link to="/permissions" className="mt-1 block text-[var(--color-link)]">
            권한 점검에서 Data Access 활성화 →
          </Link>
        ) : null}
        <p className="mt-1 text-xs text-[var(--color-neutral-60)]">
          대화는 유지됩니다 — 이 턴만 다시 보내면 됩니다.
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {turn.result?.result_type === "table" && turn.result.columns ? (
        <ResultGrid
          columns={turn.result.columns}
          rows={turn.result.rows ?? []}
          elapsedMs={turn.elapsedMs}
          truncated={turn.result.truncated}
        />
      ) : (
        <p className="whitespace-pre-wrap leading-relaxed">
          {turn.responseText ?? turn.result?.response_text ?? "(응답 없음)"}
        </p>
      )}
      {turn.result?.generated_sql ? (
        <SqlBlock
          sql={turn.result.generated_sql}
          label="생성된 SQL 보기"
          defaultOpen={sqlOpen}
          format
        />
      ) : null}
      {turn.executedSql && turn.executedSql.length > 0 ? (
        <SqlBlock
          sql={turn.executedSql}
          label="▸ 실행 SQL (params에 conversation_id 포함)"
          defaultOpen={sqlOpen}
          format
        />
      ) : null}
      {turn.elapsedMs != null ? (
        <span className="text-xs text-[var(--color-neutral-60)]">⏱ {(turn.elapsedMs / 1000).toFixed(1)}s</span>
      ) : null}
    </div>
  );
}

/** 새 대화 다이얼로그 — CREATE_CONVERSATION 속성 입력 (기본값: retention 7일 / 길이 10턴) */
function NewConversationDialog({
  onClose,
  onCreate,
  creating,
}: {
  onClose: () => void;
  onCreate: (body: ConversationCreate) => void;
  creating: boolean;
}) {
  const [title, setTitle] = useState("Demo chat");
  const [description, setDescription] = useState("Select AI demo conversation");
  const [retentionDays, setRetentionDays] = useState(7);
  const [conversationLength, setConversationLength] = useState(10);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog">
      <div className="w-[480px] rounded-[var(--radius-lg)] bg-[var(--color-neutral-0)] p-6 shadow-lg">
        <h3 className="text-lg font-semibold">새 대화 만들기</h3>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          DBMS_CLOUD_AI.CREATE_CONVERSATION이 UUID를 반환하고, 이 UUID가 모든 턴의 params로
          들어갑니다 (학습 포인트).
        </p>
        <div className="mt-4 flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm">
            제목 (title)
            <input
              className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            설명 (description)
            <input
              className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 text-sm">
              보관일 (retention_days)
              <input
                type="number"
                min={1}
                className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
                value={retentionDays}
                onChange={(e) => setRetentionDays(Number(e.target.value))}
              />
              <span className="text-xs text-[var(--color-neutral-60)]">기본 7일 (O4 결정 — 자동 삭제 없음)</span>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              맥락 길이 (conversation_length)
              <input
                type="number"
                min={1}
                className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
                value={conversationLength}
                onChange={(e) => setConversationLength(Number(e.target.value))}
              />
              <span className="text-xs text-[var(--color-neutral-60)]">LLM에 전달할 직전 턴 수</span>
            </label>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button
            loading={creating}
            onClick={() =>
              onCreate({
                title,
                description,
                retention_days: retentionDays,
                conversation_length: conversationLength,
              })
            }
          >
            대화 생성
          </Button>
        </div>
      </div>
    </div>
  );
}

export function Chat() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [conversationId, setConversationId] = useState<string>(searchParams.get("conversation") ?? "");
  const [turnAction, setTurnAction] = useState<ConversationAction>("narrate");
  const [selectedProfile, setSelectedProfile] = useState<string>("");
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<TurnView[]>([]);
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareResult, setCompareResult] = useState<{
    data: ChatCompareResult;
    executedSql: string[];
    elapsedMs: number;
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 대화 목록
  const conversationsQuery = useQuery({
    queryKey: ["chat", "conversations"],
    queryFn: () => getEnvelope<ConversationOut[]>("/chat/conversations"),
  });
  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    // 공유 키 ["profiles"] 반환 형태를 배열로 통일
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });
  const defaultProfileQuery = useQuery({
    queryKey: ["settings", "default-profile"],
    queryFn: () => getEnvelope<DefaultProfileSetting>("/settings/default-profile"),
  });
  // 추천 질문 — 프로파일 스코프(SH/OHV2) 기반
  const promptProfile = selectedProfile || defaultProfileQuery.data?.data.profile_name || "";
  const suggestedQuery = useQuery({
    queryKey: ["selectai", "suggested-prompts", promptProfile],
    queryFn: () =>
      getEnvelope<SuggestedPromptsResult>(
        `/selectai/suggested-prompts${
          promptProfile ? `?profile_name=${encodeURIComponent(promptProfile)}` : ""
        }`,
        undefined,
        { suppressErrorToast: true },
      ),
  });

  // 선택 대화의 턴 이력 (USER_CLOUD_AI_CONVERSATION_PROMPTS)
  const messagesQuery = useQuery({
    queryKey: ["chat", "messages", conversationId],
    queryFn: () => getEnvelope<ConversationMessages>(`/chat/conversations/${conversationId}/messages`),
    enabled: Boolean(conversationId),
  });

  // 대화 전환 시 서버 이력으로 로컬 턴 목록 초기화 (세션 턴은 전송 시 상세 포함으로 추가)
  useEffect(() => {
    const history = messagesQuery.data?.data.messages;
    if (history) {
      setTurns(
        history.map((message) => ({
          prompt: message.prompt,
          action: message.action,
          responseText: message.response,
        })),
      );
    } else {
      setTurns([]);
    }
    setCompareResult(null);
    // messagesQuery.data 변경(=대화 전환/재조회) 시에만 동기화
  }, [messagesQuery.data]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns, compareResult]);

  // 대화 생성
  const createMutation = useMutation({
    mutationFn: (body: ConversationCreate) => postEnvelope<ConversationOut>("/chat/conversations", body),
    onSuccess: (envelope) => {
      setShowNewDialog(false);
      setConversationId(envelope.data.conversation_id);
      void queryClient.invalidateQueries({ queryKey: ["chat", "conversations"] });
    },
  });

  // 턴 전송 — conversation_id는 백엔드가 params JSON 바인드로 전달 (SET_CONVERSATION_ID 미사용)
  const sendMutation = useMutation({
    mutationFn: (prompt: string) =>
      postEnvelope<GenerateResult>(`/chat/conversations/${conversationId}/messages`, {
        prompt,
        action: turnAction,
        profile_name: selectedProfile || null,
      }),
    onMutate: (prompt) => {
      setTurns((prev) => [...prev, { prompt, action: turnAction, pending: true }]);
      setInput("");
    },
    onSuccess: (envelope, prompt) => {
      setTurns((prev) =>
        prev.map((turn, idx) =>
          idx === prev.length - 1 && turn.pending
            ? {
                prompt,
                action: turnAction,
                result: envelope.data,
                responseText: envelope.data.response_text,
                executedSql: envelope.executed_sql,
                elapsedMs: envelope.elapsed_ms,
              }
            : turn,
        ),
      );
    },
    onError: (error, prompt) => {
      setTurns((prev) =>
        prev.map((turn, idx) =>
          idx === prev.length - 1 && turn.pending ? { prompt, action: turnAction, error } : turn,
        ),
      );
      setInput(prompt); // 실패 턴 재시도를 위해 입력 복원
    },
  });

  // 맥락 비교 — 동일 프롬프트를 conversation_id 유/무로 병렬 실행 (p132 근거)
  const compareMutation = useMutation({
    mutationFn: (prompt: string) =>
      postEnvelope<ChatCompareResult>("/chat/compare", {
        prompt,
        action: turnAction === "narrate" || turnAction === "chat" ? turnAction : "chat",
        conversation_id: conversationId,
        profile_name: selectedProfile || null,
      }),
    onSuccess: (envelope) =>
      setCompareResult({
        data: envelope.data,
        executedSql: envelope.executed_sql,
        elapsedMs: envelope.elapsed_ms,
      }),
  });

  const sqlOpen = isSqlTransparent();
  const conversations = conversationsQuery.data?.data ?? [];
  const activeConversation = conversations.find((c) => c.conversation_id === conversationId);
  const canSend = Boolean(conversationId) && input.trim().length > 0 && !sendMutation.isPending;
  const defaultProfileName = defaultProfileQuery.data?.data.profile_name;

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 — 대화 선택/생성/이력 + 프로파일 */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">챗봇 (Conversations)</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            멀티턴 대화 — 이전 질문의 맥락을 기억하는 데이터 대화를 시연합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-9 max-w-64 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2 text-sm"
            value={conversationId}
            onChange={(e) => setConversationId(e.target.value)}
          >
            <option value="">대화 선택…</option>
            {conversations.map((conversation) => (
              <option key={conversation.conversation_id} value={conversation.conversation_id}>
                {conversation.title ?? conversation.conversation_id}
              </option>
            ))}
          </select>
          <Button variant="secondary" onClick={() => setShowNewDialog(true)}>
            + 새 대화
          </Button>
          <Link to="/chat/history">
            <Button variant="ghost">이력</Button>
          </Link>
          <label className="flex items-center gap-1 text-sm">
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
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* 대화 UUID 칩 — 전문가 학습 포인트 */}
      {activeConversation ? (
        <div className="flex items-center gap-2 text-xs text-[var(--color-neutral-60)]">
          <StatusBadge status="info">conversation_id</StatusBadge>
          <code className="font-mono">{activeConversation.conversation_id}</code>
          <span>— 모든 턴의 GENERATE params에 이 UUID가 들어갑니다.</span>
        </div>
      ) : null}

      {/* 턴 액션 선택기 — 대화 지원 5종만, 기본 narrate */}
      <div className="flex items-center gap-3 text-sm">
        <span className="text-[var(--color-neutral-60)]">턴 액션:</span>
        {TURN_ACTIONS.map((action) => (
          <label key={action} className="flex items-center gap-1 font-mono">
            <input
              type="radio"
              name="turn-action"
              checked={turnAction === action}
              onChange={() => setTurnAction(action)}
            />
            {action}
          </label>
        ))}
        <span
          className="cursor-help text-[var(--color-neutral-50)]"
          title="대화에서는 runsql/showsql/explainsql/narrate/chat 5종만 지원됩니다 (가이드 p47 Note)."
        >
          ⓘ
        </span>
      </div>

      {/* 메시지 영역 */}
      <Panel className="p-0">
        <div ref={scrollRef} className="flex h-[420px] flex-col gap-4 overflow-y-auto p-6">
          {!conversationId ? (
            <div className="m-auto text-center text-[var(--color-neutral-60)]">
              <p className="text-base font-medium">새 대화를 만들어 시작하세요.</p>
              <p className="mt-2 text-sm">
                CREATE_CONVERSATION → 턴마다 GENERATE(params에 conversation_id) → 맥락 유지 멀티턴
              </p>
            </div>
          ) : turns.length === 0 && !messagesQuery.isFetching ? (
            <div className="m-auto text-center text-sm text-[var(--color-neutral-60)]">
              추천 후속 질문 칩을 순서대로 눌러 멀티턴 흐름을 시연해 보세요.
            </div>
          ) : null}

          {turns.map((turn, idx) => (
            <div key={idx} className="flex flex-col gap-2">
              {/* 사용자 버블 */}
              <div className="self-end rounded-[var(--radius-lg)] bg-[var(--color-action-primary)] px-4 py-2 text-[var(--color-neutral-0)]">
                {turn.prompt}
                {turn.action ? (
                  <span className="ml-2 font-mono text-xs opacity-70">[{turn.action}]</span>
                ) : null}
              </div>
              {/* AI 버블 */}
              <div className="max-w-[85%] self-start rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-10)] px-4 py-3 text-base">
                <TurnResponse turn={turn} />
                {idx > 0 && !turn.pending && !turn.error ? (
                  <p className="mt-2 text-xs text-[var(--color-info)]">
                    ⓘ 직전 턴의 맥락(conversation_length 범위)이 함께 LLM에 전달되었습니다.
                  </p>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        {/* 추천 질문(프로파일 스코프) + 입력 */}
        <div className="border-t border-[var(--color-neutral-30)] p-4">
          <div className="mb-2">
            <SuggestedPrompts result={suggestedQuery.data?.data} onPick={(p) => setInput(p)} />
          </div>
          <div className="flex gap-2">
            <input
              className="h-11 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
              placeholder={conversationId ? "메시지 입력…" : "먼저 대화를 선택/생성하세요"}
              disabled={!conversationId}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && canSend) sendMutation.mutate(input.trim());
              }}
            />
            <Button
              large
              loading={sendMutation.isPending}
              disabled={!canSend}
              onClick={() => sendMutation.mutate(input.trim())}
            >
              전송
            </Button>
          </div>
        </div>
      </Panel>

      {/* 맥락 비교 모드 — conversation_id 유/무 좌우 분할 (FR-07 수용 기준) */}
      <Panel>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">맥락 비교 모드</h3>
            <p className="text-sm text-[var(--color-neutral-60)]">
              같은 질문을 conversation_id 없이/있이 병렬 실행해 맥락의 효과를 증명합니다.
            </p>
          </div>
          <Button variant="secondary" onClick={() => setCompareMode((v) => !v)} disabled={!conversationId}>
            {compareMode ? "비교 모드 끄기" : "맥락 비교 모드 켜기"}
          </Button>
        </div>

        {compareMode ? (
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex gap-2">
              <input
                className="h-10 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-3"
                placeholder='비교할 질문 (예: "break out count of customers by country")'
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <Button
                loading={compareMutation.isPending}
                disabled={!input.trim() || compareMutation.isPending}
                onClick={() => compareMutation.mutate(input.trim())}
              >
                동시 실행 → 비교
              </Button>
            </div>
            {compareMutation.error ? (
              <p className="text-sm text-[var(--color-danger)]">{errorText(compareMutation.error).message}</p>
            ) : null}
            {compareResult ? (
              <>
                <ComparePanes
                  beforeTitle="conversation_id 없음 (맥락 없음)"
                  afterTitle="conversation_id 있음 (맥락 유지)"
                  before={
                    <div className="flex flex-col gap-2 text-sm">
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {compareResult.data.without_context.response_text ?? "(응답 없음)"}
                      </p>
                      {/* executed_sql[0] = params 없는 호출 (api-spec §6.7 — 호출 순서 ①②) */}
                      {compareResult.executedSql[0] ? (
                        <SqlBlock
                          sql={compareResult.executedSql[0]}
                          label="▸ 실행 SQL (params 없음)"
                          defaultOpen={sqlOpen}
                          format
                        />
                      ) : null}
                    </div>
                  }
                  after={
                    <div className="flex flex-col gap-2 text-sm">
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {compareResult.data.with_context.response_text ?? "(응답 없음)"}
                      </p>
                      {compareResult.executedSql[1] ? (
                        <SqlBlock
                          sql={compareResult.executedSql[1]}
                          label="▸ 실행 SQL (params에 conversation_id 포함)"
                          defaultOpen={sqlOpen}
                          format
                        />
                      ) : null}
                    </div>
                  }
                />
                <p className="text-sm text-[var(--color-neutral-60)]">
                  차이 요약: 오른쪽만 직전 턴 맥락을 반영합니다 — 두 SQL의 유일한 차이는{" "}
                  <code className="font-mono">params =&gt; {"{"}"conversation_id":"…"{"}"}</code> 입니다. ⏱{" "}
                  {(compareResult.elapsedMs / 1000).toFixed(1)}s
                </p>
              </>
            ) : null}
          </div>
        ) : null}
      </Panel>

      {showNewDialog ? (
        <NewConversationDialog
          onClose={() => setShowNewDialog(false)}
          onCreate={(body) => createMutation.mutate(body)}
          creating={createMutation.isPending}
        />
      ) : null}
      {createMutation.error ? (
        <p className="text-sm text-[var(--color-danger)]">{errorText(createMutation.error).message}</p>
      ) : null}
    </div>
  );
}

export default Chat;
