/**
 * Dashboard 페이지 스텁 — PG-07 (/dashboard) / FR-09 (P1).
 * 데모 상태 대시보드 — 신호등 집계.
 * 설계 근거: design.md PG-07 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Dashboard</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-07 — 구현 예정 (FR-09 (P1))
      </p>
    </div>
  );
}

export default Dashboard;
