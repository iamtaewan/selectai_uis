/**
 * ResultGrid — style.md §5.4 SQL 결과 그리드 (TanStack Table).
 * - 컬럼 자동: columns: string[] → accessorFn(row[i]) 자동 생성, 헤더 클릭 정렬
 * - 상단 메타바: 행 수 · latency(elapsed_ms, FR-06 수용 기준) · CSV 다운로드(ghost)
 * - NULL = 이탤릭 (null), 숫자 컬럼 = 우측 정렬 + tabular-nums
 * - 대용량: 100행 초과 시 페이지네이션 (§5.4 — 1000행 이상 가상 스크롤 또는 페이지네이션)
 */
import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, Download } from "lucide-react";

export interface ResultGridProps {
  columns: string[];
  rows: unknown[][];
  /** 서버 elapsed_ms (FR-06 latency 표시) */
  elapsedMs?: number | null;
  truncated?: boolean | null;
}

const PAGE_SIZE = 100;

/** CSV 셀 이스케이프 — 따옴표/콤마/개행 포함 시 큰따옴표 감싸기 */
function csvCell(value: unknown): string {
  if (value == null) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function ResultGrid({ columns, rows, elapsedMs, truncated }: ResultGridProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  // 숫자 컬럼 판정 — 첫 번째 non-null 값 기준 (우측 정렬 + tabular-nums, §5.4)
  const numericCols = useMemo(
    () =>
      columns.map((_, i) => {
        const sample = rows.find((r) => r[i] != null)?.[i];
        return typeof sample === "number";
      }),
    [columns, rows],
  );

  // 컬럼 자동 생성 — 인덱스 accessorFn (컬럼명 중복에도 안전)
  const columnDefs = useMemo<ColumnDef<unknown[]>[]>(
    () =>
      columns.map((name, i) => ({
        id: `c${i}`,
        header: name,
        accessorFn: (row) => row[i],
        sortUndefined: "last",
      })),
    [columns],
  );

  const table = useReactTable({
    data: rows,
    columns: columnDefs,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: PAGE_SIZE } },
  });

  const downloadCsv = () => {
    const csv = [
      columns.map(csvCell).join(","),
      ...rows.map((row) => row.map(csvCell).join(",")),
    ].join("\n");
    // 한글 컬럼/값 — 엑셀 호환 BOM 부착
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "selectai-result.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const pageCount = table.getPageCount();
  const pageIndex = table.getState().pagination.pageIndex;

  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)]">
      {/* 메타바 — 행 수 · latency · CSV (§5.4) */}
      <div className="flex items-center gap-3 bg-[var(--color-neutral-20)] px-3 py-1.5 text-xs text-[var(--color-neutral-60)]">
        <span className="tabular-nums">{rows.length}행</span>
        {elapsedMs != null ? <span className="tabular-nums">{elapsedMs}ms</span> : null}
        {truncated ? (
          <span className="text-[var(--color-warning)]">행 수 제한 적용됨</span>
        ) : null}
        <button
          onClick={downloadCsv}
          className="ml-auto inline-flex items-center gap-1 rounded-[var(--radius-sm)] px-2 py-0.5 text-[var(--color-link)] hover:bg-[var(--color-info-tint)]"
          disabled={rows.length === 0}
        >
          <Download size={12} aria-hidden /> CSV 다운로드
        </button>
      </div>

      <div className="max-h-[480px] overflow-auto">
        <table className="w-full border-collapse text-base">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header, i) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="sticky top-0 cursor-pointer select-none border-b border-[var(--color-neutral-40)] bg-[var(--color-neutral-20)] px-3 py-2 text-left text-sm font-medium text-[var(--color-neutral-70)]"
                    aria-sort={
                      header.column.getIsSorted() === "asc"
                        ? "ascending"
                        : header.column.getIsSorted() === "desc"
                          ? "descending"
                          : "none"
                    }
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === "asc" ? (
                        <ArrowUp size={12} aria-hidden />
                      ) : header.column.getIsSorted() === "desc" ? (
                        <ArrowDown size={12} aria-hidden />
                      ) : null}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={Math.max(columns.length, 1)}
                  className="px-3 py-6 text-center text-sm text-[var(--color-neutral-50)]"
                >
                  결과 행이 없습니다.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="h-9 hover:bg-[var(--color-neutral-10)]">
                  {row.getVisibleCells().map((cell, i) => {
                    const value = cell.getValue();
                    return (
                      <td
                        key={cell.id}
                        className={`border-b border-[var(--color-neutral-30)] px-3 py-2 ${
                          numericCols[i] ? "text-right tabular-nums" : ""
                        }`}
                      >
                        {value == null ? (
                          <span className="italic text-[var(--color-neutral-50)]">(null)</span>
                        ) : (
                          String(value)
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 페이지네이션 — 100행 초과 시에만 표시 */}
      {pageCount > 1 ? (
        <div className="flex items-center justify-end gap-2 border-t border-[var(--color-neutral-30)] bg-[var(--color-neutral-20)] px-3 py-1.5 text-xs text-[var(--color-neutral-60)]">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded-[var(--radius-sm)] px-2 py-0.5 hover:bg-[var(--color-neutral-0)] disabled:opacity-40"
          >
            이전
          </button>
          <span className="tabular-nums">
            {pageIndex + 1} / {pageCount}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded-[var(--radius-sm)] px-2 py-0.5 hover:bg-[var(--color-neutral-0)] disabled:opacity-40"
          >
            다음
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default ResultGrid;
