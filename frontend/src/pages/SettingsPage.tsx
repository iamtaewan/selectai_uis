/**
 * SettingsPage 페이지 스텁 — PG-08 (/settings) / FR-05, FR-10, 공통.
 * 앱 설정 — 기본 프로파일, 모드 전환, 데모 스키마/리소스 정리.
 * 설계 근거: design.md PG-08 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function SettingsPage() {
  return (
    <div>
      <h2 className="text-2xl font-bold">SettingsPage</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-08 — 구현 예정 (FR-05, FR-10, 공통)
      </p>
    </div>
  );
}

export default SettingsPage;
