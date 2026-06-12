/**
 * Toast 스텁 — style.md §5.8 (우상단, 상태 액센트 바, 오류는 수동 닫기).
 * 구현 담당: UI 컴포넌트 에이전트 (큐/타이머/Radix Toast 등).
 */
import type { ReactNode } from "react";

import type { BadgeStatus } from "./StatusBadge";

export interface ToastProps {
  status: BadgeStatus;
  title: string;
  children?: ReactNode;
  onClose?: () => void;
}

const ACCENT: Record<BadgeStatus, string> = {
  success: "var(--color-success)",
  error: "var(--color-danger)",
  warning: "var(--color-warning)",
  running: "var(--color-running)",
  info: "var(--color-info)",
  neutral: "var(--color-neutral-40)",
};

export function Toast({ status, title, children, onClose }: ToastProps) {
  return (
    <div
      role="status"
      className="flex w-[360px] gap-3 rounded-[var(--radius-lg)] bg-[var(--color-neutral-0)] p-4 shadow-lg"
      style={{ borderLeft: `4px solid ${ACCENT[status]}` }}
    >
      <div className="flex-1">
        <p className="font-semibold">{title}</p>
        {children ? <div className="text-sm text-[var(--color-neutral-60)]">{children}</div> : null}
      </div>
      {onClose ? (
        <button onClick={onClose} aria-label="닫기" className="text-[var(--color-neutral-60)]">
          ✕
        </button>
      ) : null}
    </div>
  );
}

export default Toast;
