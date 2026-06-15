/**
 * SuggestedPrompts — 프로파일 스코프(SH/OHV2) 기반 추천 질문 칩.
 * 데이터셋별로 묶고 난이도(단순/복잡/분석)로 구분해 표시. 클릭 = 입력 채움(자동 실행 안 함).
 * 프로파일이 SH/OHV2를 포함하지 않으면 아무것도 렌더하지 않는다.
 */
import type { SelectAIAction, SuggestedPrompt, SuggestedPromptsResult } from "../api/types";

const DATASET_LABEL: Record<string, string> = { SH: "SH (영업/판매)", OHV2: "o-home-shopping (홈쇼핑)" };
const CATEGORY_ORDER = ["단순", "복잡", "분석"];

export interface SuggestedPromptsProps {
  result?: SuggestedPromptsResult;
  onPick: (prompt: string, action: SelectAIAction) => void;
}

export function SuggestedPrompts({ result, onPick }: SuggestedPromptsProps) {
  const prompts = result?.prompts ?? [];
  if (prompts.length === 0) return null;

  // dataset → category → prompts 그룹화
  const datasets = Array.from(new Set(prompts.map((p) => p.dataset ?? "SH")));

  return (
    <div className="mt-3 flex flex-col gap-2">
      <span className="text-xs text-[var(--color-neutral-60)]">
        추천 질문 (프로파일 스코프 기반)
      </span>
      {datasets.map((ds) => (
        <div key={ds} className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold text-[var(--color-neutral-70)]">
            {DATASET_LABEL[ds] ?? ds}
          </span>
          {CATEGORY_ORDER.map((cat) => {
            const items = prompts.filter((p) => (p.dataset ?? "SH") === ds && p.category === cat);
            if (items.length === 0) return null;
            return (
              <div key={cat} className="flex flex-wrap items-center gap-2">
                <span className="w-9 shrink-0 text-xs text-[var(--color-neutral-50)]">{cat}</span>
                {items.map((s: SuggestedPrompt) => (
                  <button
                    key={s.prompt}
                    className="rounded-full border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-3 py-1 text-sm hover:bg-[var(--color-neutral-20)]"
                    onClick={() => onPick(s.prompt, s.recommended_action)}
                    title={`추천 액션: ${s.recommended_action}`}
                  >
                    {s.prompt}
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default SuggestedPrompts;
