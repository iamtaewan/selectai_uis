/**
 * Toast — style.md §5.8 (우상단, 상태 액센트 바, 오류는 수동 닫기).
 * - <Toast>: 프레젠테이션 컴포넌트 (스텁 시그니처 유지)
 * - useToastStore: 전역 토스트 큐 (api/client.ts 오류 envelope → push)
 * - <ToastContainer>: 우상단 고정 렌더러 — AppShell이 1회 마운트
 */
import { useEffect, type ReactNode } from "react";

import type { BadgeStatus } from "./StatusBadge";
import { create } from "zustand";

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
      role={status === "error" ? "alert" : "status"}
      className="flex w-[360px] gap-3 rounded-[var(--radius-lg)] bg-[var(--color-neutral-0)] p-4 shadow-lg"
      style={{ borderLeft: `4px solid ${ACCENT[status]}` }}
    >
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        {children ? (
          <div className="mt-1 break-words text-sm text-[var(--color-neutral-60)]">{children}</div>
        ) : null}
      </div>
      {onClose ? (
        <button
          onClick={onClose}
          aria-label="닫기"
          className="h-5 shrink-0 text-[var(--color-neutral-60)] hover:text-[var(--color-neutral-90)]"
        >
          ✕
        </button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------- 전역 토스트 큐

export interface ToastItem {
  id: number;
  status: BadgeStatus;
  title: string;
  /** 본문 1~2줄 (hint_ko 등) */
  body?: ReactNode;
}

interface ToastState {
  toasts: ToastItem[];
  /** 토스트 추가 — id 반환 (running → success 치환 등에 사용) */
  push: (toast: Omit<ToastItem, "id">) => number;
  dismiss: (id: number) => void;
}

let nextToastId = 1;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (toast) => {
    const id = nextToastId++;
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
    return id;
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

/** 자동 닫힘 5초(success/info/neutral) — 오류·경고는 수동 닫기 (§5.8) */
function ToastEntry({ toast }: { toast: ToastItem }) {
  const dismiss = useToastStore((s) => s.dismiss);

  useEffect(() => {
    if (toast.status === "error" || toast.status === "warning" || toast.status === "running") {
      return;
    }
    const timer = window.setTimeout(() => dismiss(toast.id), 5000);
    return () => window.clearTimeout(timer);
  }, [toast.id, toast.status, dismiss]);

  return (
    <Toast status={toast.status} title={toast.title} onClose={() => dismiss(toast.id)}>
      {toast.body}
    </Toast>
  );
}

/** 우상단 고정 토스트 렌더러 — 앱 셸 전역 1인스턴스 */
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  if (toasts.length === 0) return null;
  return (
    <div className="fixed right-4 top-16 z-50 flex flex-col gap-3">
      {toasts.map((toast) => (
        <ToastEntry key={toast.id} toast={toast} />
      ))}
    </div>
  );
}

export default Toast;
