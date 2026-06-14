/**
 * Modal — 재사용 팝업(오버레이 + 중앙 카드). Esc/배경 클릭으로 닫기.
 * style.md 토큰 사용. 메타 강화 등 항목 편집 팝업에 사용.
 */
import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

export interface ModalProps {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  /** 하단 액션 영역 (버튼 등) */
  footer?: ReactNode;
  /** 카드 최대 너비 (기본 32rem) */
  maxWidth?: string;
}

export function Modal({ open, title, onClose, children, footer, maxWidth = "36rem" }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex max-h-[85vh] w-full flex-col overflow-hidden rounded-[var(--radius-lg)] bg-[var(--color-neutral-0)] shadow-lg"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between gap-3 border-b border-[var(--color-neutral-30)] px-4 py-3">
          <h3 className="text-base font-semibold">{title}</h3>
          <button
            aria-label="닫기"
            className="rounded p-1 text-[var(--color-neutral-60)] hover:bg-[var(--color-neutral-20)]"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4">{children}</div>
        {footer ? (
          <div className="flex justify-end gap-2 border-t border-[var(--color-neutral-30)] px-4 py-3">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default Modal;
