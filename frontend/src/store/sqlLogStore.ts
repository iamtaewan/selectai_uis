/**
 * SqlLogTerminal 전역 스토어 골격 (design.md §1.3).
 * 모든 API 응답 envelope의 executed_sql[]을 클라이언트에서 누적 — 새 엔드포인트 불필요.
 * 비밀값은 서버 측 마스킹(***MASKED***) 결과를 그대로 표시 — 추가 마스킹 로직 금지.
 */
import { create } from "zustand";

export interface SqlLogLine {
  id: number;
  /** [HH:MM:SS] 타임스탬프 */
  timestamp: string;
  /** 페이지/기능 태그 (예: PG-04/runsql) — 미지정 시 요청 경로 */
  tag: string;
  sql: string;
  elapsedMs: number | null;
  ok: boolean;
  errorCode?: string;
}

export interface AppendPayload {
  sqls: string[];
  elapsedMs: number | null;
  sourcePath: string;
  ok: boolean;
  errorCode?: string;
}

interface SqlLogState {
  lines: SqlLogLine[];
  /** 패널 상태: 닫힘(기본) / 열림 / 최대화 */
  panelState: "closed" | "open" | "maximized";
  panelHeight: number;
  append: (payload: AppendPayload) => void;
  clear: () => void;
  setPanelState: (state: SqlLogState["panelState"]) => void;
  setPanelHeight: (height: number) => void;
}

let nextId = 1;

function nowTimestamp(): string {
  return new Date().toTimeString().slice(0, 8);
}

export const useSqlLogStore = create<SqlLogState>((set) => ({
  lines: [],
  panelState: "closed",
  panelHeight: 240, // 기본 240px / 최소 120px (style.md §5.9)
  append: ({ sqls, elapsedMs, sourcePath, ok, errorCode }) =>
    set((state) => ({
      lines: [
        ...state.lines,
        ...sqls.map((sql, idx) => ({
          id: nextId++,
          timestamp: nowTimestamp(),
          tag: sourcePath,
          sql,
          // elapsed_ms는 요청 단위 — 마지막 SQL 라인에만 표기
          elapsedMs: idx === sqls.length - 1 ? elapsedMs : null,
          ok,
          errorCode,
        })),
      ],
    })),
  clear: () => set({ lines: [] }),
  setPanelState: (panelState) => set({ panelState }),
  setPanelHeight: (panelHeight) => set({ panelHeight: Math.max(120, panelHeight) }),
}));
