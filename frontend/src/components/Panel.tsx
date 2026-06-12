/**
 * Panel 스텁 — style.md §4.3 카드/패널 (흰 패널 on warm paper).
 * variant="explain"은 한국어 해설/학습 패널 (FR-04, info-tint 배경).
 * 구현 담당: UI 컴포넌트 에이전트.
 */
import type { ReactNode } from "react";

export interface PanelProps {
  title?: ReactNode;
  variant?: "default" | "explain";
  children: ReactNode;
  className?: string;
}

export function Panel({ title, variant = "default", children, className = "" }: PanelProps) {
  const base =
    variant === "explain"
      ? "bg-[var(--color-info-tint)] text-[var(--color-neutral-70)] text-sm"
      : "bg-[var(--color-neutral-0)] border border-[var(--color-neutral-30)] shadow-sm";
  return (
    <section className={`rounded-[var(--radius-lg)] p-6 ${base} ${className}`}>
      {title ? <h3 className="mb-3 text-lg font-semibold">{title}</h3> : null}
      {children}
    </section>
  );
}

export default Panel;
