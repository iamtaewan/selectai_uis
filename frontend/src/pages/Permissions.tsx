/**
 * Permissions 페이지 스텁 — PG-02 (/permissions) / FR-03.
 * 권한 사전 점검 — 체크리스트 + fix_sql 미리보기 + 원클릭 적용/재점검.
 * 설계 근거: design.md PG-02 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Permissions() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Permissions</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-02 — 구현 예정 (FR-03)
      </p>
    </div>
  );
}

export default Permissions;
