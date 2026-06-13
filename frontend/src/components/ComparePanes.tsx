/**
 * ComparePanes — style.md §4.1·§4.3 좌우 분할 비교 (FR-07 대화 유무, FR-08 comments off/on).
 * - 전(before) 상단 보더 warning / 후(after) 상단 보더 success 3px 액센트
 * - 컬럼 간격 --space-6(32px), 1fr 1fr 그리드
 * - summary: 좌우 아래 전폭 "차이 요약" 슬롯 (선택)
 */
import type { ReactNode } from "react";

export interface ComparePanesProps {
  beforeTitle: ReactNode;
  afterTitle: ReactNode;
  before: ReactNode;
  after: ReactNode;
  /** 차이 요약 슬롯 — 좌우 패널 아래 전폭 렌더 (선택) */
  summary?: ReactNode;
}

export function ComparePanes({ beforeTitle, afterTitle, before, after, summary }: ComparePanesProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-8">
        <section
          className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-6 shadow-sm"
          style={{ borderTop: "3px solid var(--color-warning)" }}
          aria-label="비교 — 전"
        >
          <h3 className="mb-3 text-lg font-semibold">{beforeTitle}</h3>
          {before}
        </section>
        <section
          className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-6 shadow-sm"
          style={{ borderTop: "3px solid var(--color-success)" }}
          aria-label="비교 — 후"
        >
          <h3 className="mb-3 text-lg font-semibold">{afterTitle}</h3>
          {after}
        </section>
      </div>
      {summary ? (
        <section
          className="rounded-[var(--radius-lg)] bg-[var(--color-info-tint)] p-5 text-sm text-[var(--color-neutral-70)]"
          aria-label="차이 요약"
        >
          {summary}
        </section>
      ) : null}
    </div>
  );
}

export default ComparePanes;
