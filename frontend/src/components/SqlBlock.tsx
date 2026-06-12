/**
 * SqlBlock 스텁 — style.md §5.6 다크 코드 패널 (--color-code-* 토큰).
 * 기본은 <details> 접힘. 미리보기 모드는 "미리보기 — 아직 실행되지 않음" warning 배지.
 * 구현 담당: UI 컴포넌트 에이전트 (Shiki 구문 강조 등).
 */
export interface SqlBlockProps {
  sql: string | string[];
  /** 펼침 라벨 — 기본: "이 버튼이 실제로 실행한 SQL 보기" (P3 페르소나 문구) */
  label?: string;
  /** true면 미리보기(아직 실행 안 됨) warning 배지 표시 */
  preview?: boolean;
  /** 기본 펼침 여부 (SQL 투명 모드/전문가 모드 연동) */
  defaultOpen?: boolean;
}

export function SqlBlock({
  sql,
  label = "이 버튼이 실제로 실행한 SQL 보기",
  preview = false,
  defaultOpen = false,
}: SqlBlockProps) {
  const sqlText = Array.isArray(sql) ? sql.join("\n\n") : sql;
  return (
    <details open={defaultOpen}>
      <summary className="cursor-pointer text-sm text-[var(--color-link)]">
        {preview ? "미리보기 — 아직 실행되지 않음 · " : ""}
        {label}
      </summary>
      <pre
        className="overflow-x-auto rounded-[var(--radius-lg)] p-4 font-mono text-sm"
        style={{
          background: "var(--color-code-bg)",
          color: "var(--color-code-text)",
          lineHeight: "var(--leading-code)",
        }}
      >
        <code>{sqlText}</code>
      </pre>
    </details>
  );
}

export default SqlBlock;
