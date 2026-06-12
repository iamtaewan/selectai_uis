/**
 * Connections 페이지 스텁 — PG-01 (/connections) / FR-01, FR-02.
 * 커넥션 관리 — 목록 + 신규 연결 위저드 (wallet 업로드/OCI CLI 자동 다운로드).
 * 설계 근거: design.md PG-01 절. 구현 담당 에이전트가 본문을 채운다.
 * 라우트 등록은 App.tsx (수정 금지) — 컴포넌트 이름/기본 export 유지할 것.
 */
export function Connections() {
  return (
    <div>
      <h2 className="text-2xl font-bold">Connections</h2>
      <p className="mt-2 text-sm text-[var(--color-neutral-60)]">
        PG-01 — 구현 예정 (FR-01, FR-02)
      </p>
    </div>
  );
}

export default Connections;
