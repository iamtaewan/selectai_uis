/**
 * Field 스텁 — style.md §5.2 (라벨 위 / 해설+근거 페이지 아래 3단 구성).
 * 구현 담당: UI 컴포넌트 에이전트.
 */
import type { InputHTMLAttributes } from "react";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** 한국어 해설 (FR-04 — 21개 속성 폼) */
  helpKo?: string;
  /** 레퍼런스 근거 페이지 표기 (예: "p84") */
  docsRef?: string;
  error?: string;
}

export function Field({ label, helpKo, docsRef, error, id, className = "", ...rest }: FieldProps) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        className={`h-9 rounded-[var(--radius-sm)] border px-3 text-base ${
          error ? "border-[var(--color-danger)]" : "border-[var(--color-neutral-40)]"
        } bg-[var(--color-neutral-0)]`}
        {...rest}
      />
      {helpKo ? (
        <p className="text-xs text-[var(--color-neutral-60)]">
          {helpKo}
          {docsRef ? <span className="ml-1 text-[var(--color-info)]">({docsRef})</span> : null}
        </p>
      ) : null}
      {error ? <p className="text-sm text-[var(--color-danger)]">{error}</p> : null}
    </div>
  );
}

export default Field;
