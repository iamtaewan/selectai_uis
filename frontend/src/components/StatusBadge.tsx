/**
 * StatusBadge 스텁 — style.md §5.7 (tint 배경 + 본색 텍스트).
 * 구현 담당: UI 컴포넌트 에이전트.
 */
import type { ReactNode } from "react";

export type BadgeStatus = "success" | "error" | "warning" | "running" | "info" | "neutral";

export interface StatusBadgeProps {
  status: BadgeStatus;
  children: ReactNode;
}

const STATUS_CLASS: Record<BadgeStatus, string> = {
  success: "bg-[var(--color-success-tint)] text-[var(--color-success)]",
  error: "bg-[var(--color-danger-tint)] text-[var(--color-danger)]",
  warning: "bg-[var(--color-warning-tint)] text-[var(--color-warning)]",
  running: "bg-[var(--color-running-tint)] text-[var(--color-running)]",
  info: "bg-[var(--color-info-tint)] text-[var(--color-info)]",
  neutral: "bg-[var(--color-neutral-20)] text-[var(--color-neutral-60)]",
};

export function StatusBadge({ status, children }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex h-[22px] items-center gap-1 rounded-full px-2 text-xs font-medium ${STATUS_CLASS[status]}`}
    >
      {children}
    </span>
  );
}

export default StatusBadge;
