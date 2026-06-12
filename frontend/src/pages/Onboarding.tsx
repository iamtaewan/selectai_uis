/**
 * Onboarding 페이지 스텁 — PG-00 (/) / 공통.
 * 온보딩/시작 화면 — 첫 실행 가이드, 데모 여정 안내.
 * 설계 근거: design.md PG-00 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Onboarding() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Onboarding</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-00 — 구현 예정 (공통)
      </p>
    </div>
  );
}

export default Onboarding;
