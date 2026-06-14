/**
 * Button — Redwood (primary=Oracle Red 채움+흰 글자 / secondary=뉴트럴 외곽선 / danger / ghost).
 * 한 화면에 빨강 primary는 가급적 하나 — 보조 액션은 variant="secondary".
 * 공통: 높이 36px(기본)/44px(large), radius-md, semibold.
 * hover 시 배경 1단계 어둡게, :focus-visible 링은 tokens.css 전역 규칙 사용.
 * 로딩 중 = 스피너 + 비활성 (LLM 호출 중복 방지 — §5.1).
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

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
  primary:
    "bg-[var(--color-action-primary)] text-[var(--color-neutral-0)] hover:bg-[var(--color-action-primary-hover)]",
  secondary:
    "bg-[var(--color-neutral-0)] text-[var(--color-neutral-90)] border border-[var(--color-neutral-40)] hover:bg-[var(--color-neutral-20)]",
  danger: "bg-[var(--color-danger)] text-[var(--color-neutral-0)] hover:bg-[var(--color-brand-dark)]",
  ghost: "bg-transparent text-[var(--color-link)] hover:bg-[var(--color-info-tint)]",
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
  const inactive = disabled || loading;
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 text-base font-semibold transition-colors ${
        large ? "h-11" : "h-9"
      } ${VARIANT_CLASS[variant]} ${
        inactive ? "cursor-not-allowed opacity-50 hover:bg-[unset]" : ""
      } ${className}`}
      disabled={inactive}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="animate-spin" aria-label="처리 중" /> : null}
      {children}
    </button>
  );
}

export default Button;
