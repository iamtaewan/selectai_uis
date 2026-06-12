/**
 * ComparePanes 스텁 — style.md §4.1·§4.3 좌우 분할 비교 (FR-07 맥락, FR-08 증강).
 * 전(before) 상단 보더 warning / 후(after) 상단 보더 success 3px 액센트.
 * 구현 담당: UI 컴포넌트 에이전트.
 */
import type { ReactNode } from "react";

export interface ComparePanesProps {
  beforeTitle: ReactNode;
  afterTitle: ReactNode;
  before: ReactNode;
  after: ReactNode;
}

export function ComparePanes({ beforeTitle, afterTitle, before, after }: ComparePanesProps) {
  return (
    <div className="grid grid-cols-2 gap-8">
      <section
        className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-6"
        style={{ borderTop: "3px solid var(--color-warning)" }}
      >
        <h3 className="mb-3 text-lg font-semibold">{beforeTitle}</h3>
        {before}
      </section>
      <section
        className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-6"
        style={{ borderTop: "3px solid var(--color-success)" }}
      >
        <h3 className="mb-3 text-lg font-semibold">{afterTitle}</h3>
        {after}
      </section>
    </div>
  );
}

export default ComparePanes;
