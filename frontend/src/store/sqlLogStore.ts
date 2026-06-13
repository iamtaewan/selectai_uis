/**
 * SqlLogTerminal 전역 스토어 (design.md §1.3).
 * 모든 API 응답 envelope의 executed_sql[]을 클라이언트에서 누적 — 새 엔드포인트 불필요.
 * 비밀값은 서버 측 마스킹(***MASKED***) 결과를 그대로 표시 — 추가 마스킹 로직 금지.
 * 로그는 전역 상태로 페이지를 이동해도 세션 내 유지된다.
 *
 * 라인 상태 3종(design §1.3): 성공(기본) / 오류(danger) / 실행 중(running 스피너).
 * 실행 중 라인은 beginRunning()으로 추가되고, 완료 시 resolveRunning()이
 * 같은 위치에서 실제 SQL 라인으로 치환한다 (시계열 순서 유지).
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
  /** true면 실행 중 라인 — 완료 시 실제 SQL 라인으로 치환됨 */
  running?: boolean;
}

export interface AppendPayload {
  sqls: string[];
  elapsedMs: number | null;
  sourcePath: string;
  ok: boolean;
  errorCode?: string;
  /** 페이지/기능 태그 — 지정 시 sourcePath보다 우선 표시 */
  tag?: string;
}

interface SqlLogState {
  lines: SqlLogLine[];
  /** 패널 상태: 닫힘(기본) / 열림 / 최대화 */
  panelState: "closed" | "open" | "maximized";
  panelHeight: number;
  append: (payload: AppendPayload) => void;
  /** 실행 중 라인 추가 — 반환된 id로 resolveRunning 호출 */
  beginRunning: (tag: string) => number;
  /** 실행 중 라인을 실제 라인으로 치환(payload) 또는 제거(null — executed_sql 없는 완료) */
  resolveRunning: (id: number, payload: AppendPayload | null) => void;
  clear: () => void;
  setPanelState: (state: SqlLogState["panelState"]) => void;
  /** 열기/닫기 토글 — 푸터 상태바 · Ctrl/Cmd+` 단축키 공용 */
  togglePanel: () => void;
  setPanelHeight: (height: number) => void;
}

let nextId = 1;

function nowTimestamp(): string {
  return new Date().toTimeString().slice(0, 8);
}

/** AppendPayload → 로그 라인 배열 (elapsed_ms는 요청 단위 — 마지막 SQL 라인에만 표기) */
function toLines(payload: AppendPayload): SqlLogLine[] {
  const { sqls, elapsedMs, sourcePath, ok, errorCode, tag } = payload;
  const timestamp = nowTimestamp();
  return sqls.map((sql, idx) => ({
    id: nextId++,
    timestamp,
    tag: tag ?? sourcePath,
    sql,
    elapsedMs: idx === sqls.length - 1 ? elapsedMs : null,
    ok,
    errorCode,
  }));
}

export const useSqlLogStore = create<SqlLogState>((set) => ({
  lines: [],
  panelState: "closed",
  panelHeight: 240, // 기본 240px / 최소 120px (style.md §5.9)
  append: (payload) => set((state) => ({ lines: [...state.lines, ...toLines(payload)] })),
  beginRunning: (tag) => {
    const id = nextId++;
    set((state) => ({
      lines: [
        ...state.lines,
        { id, timestamp: nowTimestamp(), tag, sql: "", elapsedMs: null, ok: true, running: true },
      ],
    }));
    return id;
  },
  resolveRunning: (id, payload) =>
    set((state) => {
      const idx = state.lines.findIndex((line) => line.id === id);
      if (idx < 0) {
        // 실행 중에 clear된 경우 — 완료 라인만 뒤에 누적
        return payload ? { lines: [...state.lines, ...toLines(payload)] } : {};
      }
      const lines = [...state.lines];
      lines.splice(idx, 1, ...(payload ? toLines(payload) : []));
      return { lines };
    }),
  clear: () => set({ lines: [] }),
  setPanelState: (panelState) => set({ panelState }),
  togglePanel: () =>
    set((state) => ({ panelState: state.panelState === "closed" ? "open" : "closed" })),
  setPanelHeight: (panelHeight) => set({ panelHeight: Math.max(120, panelHeight) }),
}));
