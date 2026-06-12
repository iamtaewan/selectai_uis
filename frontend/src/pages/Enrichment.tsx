/**
 * Enrichment 페이지 스텁 — PG-06 (/enrichment) / FR-08.
 * Comment 증강 전/후 비교 — 모호 스키마, COMMENT DDL, 프로파일 쌍, 좌우 비교.
 * 설계 근거: design.md PG-06 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Enrichment() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Enrichment</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-06 — 구현 예정 (FR-08)
      </p>
    </div>
  );
}

export default Enrichment;
