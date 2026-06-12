/**
 * ProfileEditor 페이지 스텁 — PG-03a (/profiles/new · /profiles/:name/edit) / FR-04.
 * 프로파일 생성/편집 — 검증 21개 속성 폼 + 한국어 해설 + object_list 브라우저.
 * 설계 근거: design.md PG-03a 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function ProfileEditor() {
  return (
    <div>
      <h2 className="text-2xl font-bold">ProfileEditor</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-03a — 구현 예정 (FR-04)
      </p>
    </div>
  );
}

export default ProfileEditor;
