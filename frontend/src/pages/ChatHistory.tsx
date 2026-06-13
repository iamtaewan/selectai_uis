/**
 * ChatHistory 페이지 — PG-05a (/chat/history) / FR-07.
 * 대화 목록(USER_CLOUD_AI_CONVERSATIONS) + 행 펼침 턴 이력(USER_CLOUD_AI_CONVERSATION_PROMPTS).
 * 근거: design.md §3 PG-05a, api-spec §6.3·§6.4·§6.6.
 * - [이 대화 이어가기] → /chat?conversation=<id> 딥링크 (Chat.tsx가 쿼리로 자동 선택)
 * - [삭제] → DROP_CONVERSATION SQL 미리보기 + 확인 다이얼로그 (design.md §5 원칙 5 — 2단계)
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { deleteEnvelope, getEnvelope } from "../api/client";
import type { ChatMessageOut, ConversationOut } from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";

/** 턴 이력 API 응답 형태 (api-spec §6.4) */
interface ConversationMessages {
  conversation_id: string;
  messages: ChatMessageOut[];
}

/** 행 펼침 — 선택 대화의 턴 이력 조회 */
function TurnHistory({ conversationId }: { conversationId: string }) {
  const messagesQuery = useQuery({
    queryKey: ["chat", "messages", conversationId],
    queryFn: () =>
      getEnvelope<ConversationMessages>(`/chat/conversations/${conversationId}/messages`),
  });

  if (messagesQuery.isPending) {
    return <p className="p-4 text-sm text-[var(--color-neutral-60)]">◌ 턴 이력 조회 중…</p>;
  }
  if (messagesQuery.error) {
    return (
      <p className="p-4 text-sm text-[var(--color-danger)]">
        턴 이력을 불러오지 못했습니다 — 행을 다시 펼쳐 재시도하세요.
      </p>
    );
  }
  const messages = messagesQuery.data?.data.messages ?? [];
  if (messages.length === 0) {
    return <p className="p-4 text-sm text-[var(--color-neutral-60)]">아직 턴이 없는 대화입니다.</p>;
  }
  return (
    <div className="flex flex-col gap-3 p-4">
      {messages.map((message) => (
        <div key={message.prompt_id} className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-sm">
            <StatusBadge status="neutral">{message.action ?? "narrate"}</StatusBadge>
            <span className="font-medium">{message.prompt}</span>
            {message.created_at ? (
              <span className="text-xs text-[var(--color-neutral-50)]">{message.created_at}</span>
            ) : null}
          </div>
          <p className="whitespace-pre-wrap rounded-[var(--radius-md)] bg-[var(--color-neutral-10)] p-3 text-sm leading-relaxed">
            {message.response ?? "(응답 없음)"}
          </p>
        </div>
      ))}
    </div>
  );
}

/** 삭제 확인 다이얼로그 — DROP_CONVERSATION 미리보기 필수 (파괴적 작업 2단계) */
function DeleteDialog({
  conversation,
  deleting,
  onCancel,
  onConfirm,
}: {
  conversation: ConversationOut;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog">
      <div className="w-[520px] rounded-[var(--radius-lg)] bg-[var(--color-neutral-0)] p-6 shadow-lg">
        <h3 className="text-lg font-semibold">대화 삭제</h3>
        <p className="mt-2 text-sm text-[var(--color-neutral-70)]">
          「{conversation.title ?? conversation.conversation_id}」 대화와 모든 턴 이력이
          삭제됩니다. 되돌릴 수 없습니다.
        </p>
        <div className="mt-3">
          {/* 실행될 SQL 미리보기 — 백엔드는 바인드 변수로 실행 (표시는 학습용 원문 패턴) */}
          <SqlBlock
            sql={`BEGIN\n  DBMS_CLOUD_AI.DROP_CONVERSATION(:conversation_id);\nEND;\n-- :conversation_id = '${conversation.conversation_id}'`}
            label="실행될 SQL 보기"
            preview
            defaultOpen
          />
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            취소
          </Button>
          <Button variant="danger" loading={deleting} onClick={onConfirm}>
            삭제 실행
          </Button>
        </div>
      </div>
    </div>
  );
}

/** 대화 1행 + 펼침 행 — 제목/보관일/길이 + 이어가기/삭제 액션 */
function ConversationRow({
  conversation,
  expanded,
  onToggle,
  onDelete,
}: {
  conversation: ConversationOut;
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  return (
    <>
      <tr
        className="cursor-pointer border-t border-[var(--color-neutral-30)] hover:bg-[var(--color-neutral-10)]"
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          <span className="mr-2 inline-block w-4 text-[var(--color-neutral-50)]">
            {expanded ? "▾" : "▸"}
          </span>
          <span className="font-medium">{conversation.title ?? "(제목 없음)"}</span>
          <code className="ml-2 font-mono text-xs text-[var(--color-neutral-50)]">
            {conversation.conversation_id}
          </code>
        </td>
        <td className="px-4 py-3 text-sm text-[var(--color-neutral-60)]">
          {conversation.description ?? "—"}
        </td>
        <td className="px-4 py-3 text-sm">
          {conversation.retention_days != null ? `${conversation.retention_days}일` : "—"}
        </td>
        <td className="px-4 py-3 text-sm">
          {conversation.conversation_length != null ? `${conversation.conversation_length}턴` : "—"}
        </td>
        <td className="px-4 py-3">
          <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
            <Link to={`/chat?conversation=${conversation.conversation_id}`}>
              <Button variant="ghost">이 대화 이어가기 →</Button>
            </Link>
            <Button variant="danger" onClick={onDelete}>
              삭제
            </Button>
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr className="border-t border-[var(--color-neutral-30)] bg-[var(--color-neutral-10)]">
          <td colSpan={5}>
            <TurnHistory conversationId={conversation.conversation_id} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function ChatHistory() {
  const queryClient = useQueryClient();
  const pushToast = useToastStore((s) => s.push);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ConversationOut | null>(null);

  // 대화 목록 (USER_CLOUD_AI_CONVERSATIONS)
  const conversationsQuery = useQuery({
    queryKey: ["chat", "conversations"],
    queryFn: () => getEnvelope<ConversationOut[]>("/chat/conversations"),
  });

  // 대화 삭제 — DROP_CONVERSATION (api-spec §6.6)
  const deleteMutation = useMutation({
    mutationFn: (conversationId: string) =>
      deleteEnvelope<unknown>(`/chat/conversations/${conversationId}`, {
        sqlLogTag: "PG-05a/drop",
      }),
    onSuccess: (_envelope, conversationId) => {
      setDeleteTarget(null);
      if (expandedId === conversationId) setExpandedId(null);
      pushToast({ status: "success", title: "대화가 삭제되었습니다 (DROP_CONVERSATION)" });
      void queryClient.invalidateQueries({ queryKey: ["chat", "conversations"] });
    },
  });

  const conversations = conversationsQuery.data?.data ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">대화 이력</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            USER_CLOUD_AI_CONVERSATIONS의 대화 목록 — 행을 펼치면 턴 이력이 보입니다.
          </p>
        </div>
        <Link to="/chat">
          <Button variant="secondary">← 챗봇으로</Button>
        </Link>
      </div>

      <Panel className="p-0">
        {conversationsQuery.isPending ? (
          <p className="p-6 text-sm text-[var(--color-neutral-60)]">◌ 대화 목록 조회 중…</p>
        ) : conversations.length === 0 ? (
          <div className="p-8 text-center text-[var(--color-neutral-60)]">
            <p>저장된 대화가 없습니다.</p>
            <Link to="/chat" className="mt-2 inline-block text-[var(--color-link)]">
              챗봇에서 새 대화 만들기 →
            </Link>
          </div>
        ) : (
          <table className="w-full text-base">
            <thead>
              <tr className="bg-[var(--color-neutral-20)] text-left text-sm text-[var(--color-neutral-70)]">
                <th className="px-4 py-2 font-medium">제목</th>
                <th className="px-4 py-2 font-medium">설명</th>
                <th className="px-4 py-2 font-medium">보관일</th>
                <th className="px-4 py-2 font-medium">맥락 길이</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {conversations.map((conversation) => (
                <ConversationRow
                  key={conversation.conversation_id}
                  conversation={conversation}
                  expanded={expandedId === conversation.conversation_id}
                  onToggle={() =>
                    setExpandedId((prev) =>
                      prev === conversation.conversation_id ? null : conversation.conversation_id,
                    )
                  }
                  onDelete={() => setDeleteTarget(conversation)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {deleteTarget ? (
        <DeleteDialog
          conversation={deleteTarget}
          deleting={deleteMutation.isPending}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => deleteMutation.mutate(deleteTarget.conversation_id)}
        />
      ) : null}
    </div>
  );
}

export default ChatHistory;
