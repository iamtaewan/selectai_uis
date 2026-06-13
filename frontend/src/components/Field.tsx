/**
 * Field — style.md §5.2 (라벨 위 / 입력 / 해설+근거 페이지 아래 3단 구성).
 * - 라벨 옆 ⓘ 툴팁 슬롯(tooltip) — hover/focus 시 표시 (FR-04 속성 폼 보조 설명)
 * - type="password"는 표시 토글 제공, 값은 어떤 UI 텍스트에도 에코하지 않음 (§5.2)
 * - 기존 스텁 props(label/helpKo/docsRef/error) 유지 — tooltip만 확장.
 */
import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { Eye, EyeOff, Info } from "lucide-react";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** 한국어 해설 (FR-04 — 21개 속성 폼) */
  helpKo?: string;
  /** 레퍼런스 근거 페이지 표기 (예: "p84") */
  docsRef?: string;
  error?: string;
  /** 라벨 옆 ⓘ 툴팁 슬롯 — hover/focus 시 표시 */
  tooltip?: ReactNode;
}

export function Field({
  label,
  helpKo,
  docsRef,
  error,
  tooltip,
  id,
  type,
  className = "",
  ...rest
}: FieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <span className="flex items-center gap-1">
        <label htmlFor={fieldId} className="text-sm font-medium">
          {label}
        </label>
        {tooltip ? (
          // ⓘ 툴팁 — CSS only (hover/focus-within), style §5.8 그림자/라운딩 토큰
          <span className="group relative inline-flex" tabIndex={0}>
            <Info
              size={14}
              className="text-[var(--color-neutral-50)] group-hover:text-[var(--color-info)]"
              aria-label="설명"
            />
            <span
              role="tooltip"
              className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-1 hidden w-64 -translate-x-1/2 rounded-[var(--radius-md)] bg-[var(--color-neutral-80)] px-3 py-2 text-xs font-normal text-[var(--color-neutral-10)] shadow-lg group-hover:block group-focus:block"
            >
              {tooltip}
            </span>
          </span>
        ) : null}
      </span>

      <span className="relative flex">
        <input
          id={fieldId}
          type={isPassword && showPassword ? "text" : type}
          aria-invalid={!!error || undefined}
          aria-describedby={helpKo || error ? `${fieldId}-desc` : undefined}
          className={`h-9 w-full rounded-[var(--radius-sm)] border bg-[var(--color-neutral-0)] px-3 text-base focus:border-[var(--color-focus-ring)] focus:shadow-[0_0_0_1px_var(--color-focus-ring)] focus:outline-none ${
            error ? "border-[var(--color-danger)]" : "border-[var(--color-neutral-40)]"
          } ${isPassword ? "pr-9" : ""}`}
          {...rest}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 표시"}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-neutral-50)] hover:text-[var(--color-neutral-90)]"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        ) : null}
      </span>

      {helpKo || error ? (
        <p id={`${fieldId}-desc`} className="text-xs">
          {error ? (
            <span className="text-sm text-[var(--color-danger)]">{error}</span>
          ) : (
            <span className="text-[var(--color-neutral-60)]">
              {helpKo}
              {docsRef ? <span className="ml-1 text-[var(--color-info)]">({docsRef})</span> : null}
            </span>
          )}
        </p>
      ) : null}
    </div>
  );
}

export default Field;
