/**
 * ChatHistory 페이지 스텁 — PG-05a (/chat/history) / FR-07.
 * 대화 목록/이력 관리 — 일괄 삭제(DROP_CONVERSATION).
 * 설계 근거: design.md PG-05a 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function ChatHistory() {
  return (
    <div>
      <h2 className="text-2xl font-bold">ChatHistory</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-05a — 구현 예정 (FR-07)
      </p>
    </div>
  );
}

export default ChatHistory;
