/**
 * Playground 페이지 스텁 — PG-04 (/playground) / FR-06.
 * Select AI 플레이그라운드 — 액션 탭(runsql/showsql/explainsql/narrate/chat) 시연.
 * 설계 근거: design.md PG-04 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Playground() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Playground</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-04 — 구현 예정 (FR-06)
      </p>
    </div>
  );
}

export default Playground;
