/**
 * Button 스텁 — style.md §5.1 (primary=잉크 / secondary / danger / ghost).
 * 구현 담당: UI 컴포넌트 에이전트. props 시그니처는 유지할 것.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /** LLM 호출 등 장시간 작업 — 스피너 + 비활성 (중복 호출 방지) */
  loading?: boolean;
  /** P2 큰 타깃(44px) — 추천 프롬프트 등 */
  large?: boolean;
  children: ReactNode;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "bg-[var(--color-action-primary)] text-[var(--color-neutral-0)]",
  secondary:
    "bg-[var(--color-neutral-0)] text-[var(--color-neutral-90)] border border-[var(--color-neutral-40)]",
  danger: "bg-[var(--color-danger)] text-[var(--color-neutral-0)]",
  ghost: "bg-transparent text-[var(--color-link)]",
};

export function Button({
  variant = "primary",
  loading = false,
  large = false,
  children,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 font-semibold ${
        large ? "h-11" : "h-9"
      } ${VARIANT_CLASS[variant]} ${disabled || loading ? "opacity-50" : ""} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? "…" : null}
      {children}
    </button>
  );
}

export default Button;
