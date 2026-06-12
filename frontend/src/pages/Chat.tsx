/**
 * Chat 페이지 스텁 — PG-05 (/chat) / FR-07.
 * 챗봇(Conversations) — 턴 실행 + 맥락 비교 모드.
 * 설계 근거: design.md PG-05 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Chat() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Chat</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-05 — 구현 예정 (FR-07)
      </p>
    </div>
  );
}

export default Chat;
