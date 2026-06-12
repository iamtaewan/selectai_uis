/**
 * ResultGrid 스텁 — style.md §5.4 SQL 결과 그리드 (TanStack Table 기반 예정).
 * 상단 메타바: 행 수 · latency · CSV 다운로드. NULL은 이탤릭 (null).
 * 구현 담당: UI 컴포넌트 에이전트.
 */
export interface ResultGridProps {
  columns: string[];
  rows: unknown[][];
  /** 서버 elapsed_ms (FR-06 latency 표시) */
  elapsedMs?: number | null;
  truncated?: boolean | null;
}

export function ResultGrid({ columns, rows, elapsedMs, truncated }: ResultGridProps) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)]">
      <div className="flex gap-3 bg-[var(--color-neutral-20)] px-3 py-2 text-xs text-[var(--color-neutral-60)]">
        <span>{rows.length}행</span>
        {elapsedMs != null ? <span>{elapsedMs}ms</span> : null}
        {truncated ? <span>행 수 제한 적용됨</span> : null}
      </div>
      <table className="w-full text-base">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="border-b border-[var(--color-neutral-40)] bg-[var(--color-neutral-20)] px-3 py-2 text-left text-sm font-medium text-[var(--color-neutral-70)]"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-[var(--color-neutral-10)]">
              {row.map((cell, j) => (
                <td key={j} className="border-b border-[var(--color-neutral-30)] px-3 py-2">
                  {cell == null ? (
                    <span className="italic text-[var(--color-neutral-50)]">(null)</span>
                  ) : (
                    String(cell)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ResultGrid;
