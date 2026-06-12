/**
 * SqlLogTerminal 스텁 — design.md §1.3 / style.md §5.9.
 * VS Code 통합 터미널 스타일 하단 도킹 패널 — 앱 셸 전역 1인스턴스.
 * 데이터 소스: sqlLogStore (모든 envelope의 executed_sql[] 누적).
 * 구현 담당: UI 컴포넌트 에이전트 (드래그 리사이즈, Ctrl/Cmd+` 토글, 구문 강조 등).
 */
import { useSqlLogStore } from "../store/sqlLogStore";

export function SqlLogTerminal() {
  const { lines, panelState, panelHeight, setPanelState, clear } = useSqlLogStore();

  if (panelState === "closed") return null;

  return (
    <div
      className="flex flex-col font-mono text-sm"
      style={{
        height: panelState === "maximized" ? "100%" : panelHeight,
        background: "var(--color-code-bg)",
        color: "var(--color-code-text)",
        borderTop: "1px solid var(--color-neutral-40)",
      }}
    >
      {/* 헤더 바 — SQL LOG 타이틀 + 카운트 + 지우기/복사/최대화/닫기 */}
      <div
        className="flex h-8 items-center justify-between px-3"
        style={{ background: "var(--color-neutral-80)" }}
      >
        <span className="text-xs font-semibold tracking-[0.08em]">
          SQL LOG{" "}
          <span className="rounded-full bg-white/10 px-2">{lines.length}</span>
        </span>
        <span className="flex gap-2">
          <button onClick={clear} aria-label="지우기">⌫</button>
          <button
            onClick={() => setPanelState(panelState === "maximized" ? "open" : "maximized")}
            aria-label="최대화/복원"
          >
            ▢
          </button>
          <button onClick={() => setPanelState("closed")} aria-label="닫기">✕</button>
        </span>
      </div>
      {/* 로그 라인 — [HH:MM:SS] [태그] SQL — 123ms */}
      <div className="flex-1 overflow-y-auto p-3" style={{ lineHeight: "var(--leading-code)" }}>
        {lines.map((line) => (
          <div
            key={line.id}
            style={line.ok ? undefined : { borderLeft: "2px solid var(--color-danger)" }}
          >
            <span style={{ color: "var(--color-code-comment)" }}>[{line.timestamp}]</span>{" "}
            <span style={{ color: "var(--color-code-accent)" }}>[{line.tag}]</span> {line.sql}
            {line.elapsedMs != null ? (
              <span style={{ color: "var(--color-code-comment)" }}> — {line.elapsedMs}ms</span>
            ) : null}
            {line.errorCode ? (
              <span style={{ color: "var(--color-danger)" }}> ✗ {line.errorCode}</span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export default SqlLogTerminal;
