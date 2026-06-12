/**
 * ProfileDetail 페이지 스텁 — PG-03b (/profiles/:name) / FR-05.
 * 프로파일 속성 상세 (읽기 전용) — USER_CLOUD_AI_PROFILE_ATTRIBUTES 뷰 기반.
 * 설계 근거: design.md PG-03b 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function ProfileDetail() {
  return (
    <div>
      <h2 className="text-2xl font-bold">ProfileDetail</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-03b — 구현 예정 (FR-05)
      </p>
    </div>
  );
}

export default ProfileDetail;
