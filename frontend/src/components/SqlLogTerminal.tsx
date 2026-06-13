/**
 * SqlLogTerminal — design.md §1.3 / style.md §5.9 완전 구현.
 * VS Code 통합 터미널 스타일 하단 도킹 패널 — 앱 셸 전역 1인스턴스.
 * 데이터 소스: sqlLogStore (모든 envelope의 executed_sql[] 누적 — 새 엔드포인트 불필요).
 *
 * - 상태 3종: 닫힘(기본, 푸터 배지만) / 열림(드래그 높이 조절, 기본 240/최소 120) / 최대화
 * - 단축키: Ctrl/Cmd + ` 토글 (닫힘 상태에서도 동작 — 항상 마운트, 닫힘 시 null 렌더)
 * - 닫힌 상태에서 새 로그 발생 시 푸터 카운트 배지만 갱신 — 자동 오픈 금지 (인터랙션 원칙 5)
 * - 로그 라인: [HH:MM:SS][태그] SQL — 123ms (성공 기본 / 오류 danger / 실행 중 running 스피너)
 */
import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { Check, Copy, Loader2, Maximize2, Minimize2, Trash2, X } from "lucide-react";

import { useSqlLogStore, type SqlLogLine } from "../store/sqlLogStore";
import { highlightSql } from "./SqlBlock";

/** 로그 라인 1개 — [타임스탬프][태그] SQL — latency (style §5.9 라인 상태) */
function LogLine({ line }: { line: SqlLogLine }) {
  return (
    <div
      className="whitespace-pre-wrap break-all py-0.5 pl-2"
      style={line.ok ? undefined : { borderLeft: "2px solid var(--color-danger)" }}
    >
      <span style={{ color: "var(--color-code-comment)" }}>[{line.timestamp}]</span>{" "}
      <span style={{ color: "var(--color-code-accent)" }}>[{line.tag}]</span>{" "}
      {line.running ? (
        <span style={{ color: "var(--color-running)" }}>
          <Loader2 size={13} className="inline animate-spin align-[-2px]" /> 실행 중…
        </span>
      ) : (
        <>
          {highlightSql(line.sql)}
          {line.elapsedMs != null ? (
            <span style={{ color: "var(--color-code-comment)" }}> — {line.elapsedMs}ms</span>
          ) : null}
          {line.errorCode ? (
            <span style={{ color: "var(--color-danger)" }}> ✗ {line.errorCode}</span>
          ) : null}
        </>
      )}
    </div>
  );
}

export function SqlLogTerminal() {
  const { lines, panelState, panelHeight, setPanelState, setPanelHeight, clear } =
    useSqlLogStore();
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Ctrl/Cmd + ` 토글 — 닫힘 상태에서도 동작해야 하므로 항상 등록
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        useSqlLogStore.getState().togglePanel();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // 새 로그 발생 시 하단 자동 스크롤 (터미널 동작)
  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length, panelState]);

  // 드래그 높이 조절 — 상단 6px 핸들 (style §5.9)
  const onDragStart = (e: ReactMouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = panelHeight;
    setDragging(true);
    const onMove = (ev: MouseEvent) => {
      const next = Math.min(window.innerHeight - 160, startHeight + (startY - ev.clientY));
      setPanelHeight(next); // 스토어가 최소 120 클램프
    };
    const onUp = () => {
      setDragging(false);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const copyAll = async () => {
    const text = lines
      .filter((l) => !l.running)
      .map(
        (l) =>
          `[${l.timestamp}] [${l.tag}] ${l.sql}` +
          (l.elapsedMs != null ? ` — ${l.elapsedMs}ms` : "") +
          (l.errorCode ? ` ✗ ${l.errorCode}` : ""),
      )
      .join("\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  // 닫힘 상태 — 푸터 상태바 배지만 남김 (자동 오픈 금지). 단축키 리스너는 위에서 유지.
  if (panelState === "closed") return null;

  const maximized = panelState === "maximized";
  const iconBtn =
    "inline-flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] hover:bg-white/10";

  return (
    <div
      className="flex shrink-0 flex-col font-mono text-sm"
      style={{
        height: maximized ? "100%" : panelHeight,
        background: "var(--color-code-bg)",
        color: "var(--color-code-text)",
        borderTop: "1px solid var(--color-neutral-40)",
      }}
      role="log"
      aria-label="SQL 로그 터미널"
      tabIndex={0}
      onKeyDown={(e) => {
        // §5.9 키보드: Esc = 닫기, ↑/↓ = 라인 단위 스크롤 탐색
        if (e.key === "Escape") {
          setPanelState("closed");
        } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          e.preventDefault();
          const el = bodyRef.current;
          if (el) el.scrollTop += e.key === "ArrowDown" ? 24 : -24;
        }
      }}
    >
      {/* 상단 6px 드래그 핸들 — hover·드래그 중 focus-ring 표시 (최대화 상태에선 비활성) */}
      {!maximized ? (
        <div
          onMouseDown={onDragStart}
          className="h-[6px] shrink-0 cursor-row-resize"
          style={{ background: dragging ? "var(--color-focus-ring)" : "transparent" }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = "var(--color-focus-ring)";
          }}
          onMouseLeave={(e) => {
            if (!dragging) (e.currentTarget as HTMLDivElement).style.background = "transparent";
          }}
          aria-hidden
        />
      ) : null}

      {/* 헤더 바 32px — 타이틀 + 카운트 배지 + 지우기/복사/최대화/닫기 (§5.9) */}
      <div
        className="flex h-8 shrink-0 items-center justify-between px-3"
        style={{ background: "var(--color-neutral-80)" }}
      >
        <span className="text-xs font-semibold tracking-[0.08em]">
          SQL LOG{" "}
          <span
            className="rounded-full px-2"
            style={{ background: "rgba(255,255,255,0.12)", color: "var(--color-code-text)" }}
          >
            {lines.length}
          </span>
        </span>
        <span className="flex items-center gap-1">
          {/* 지우기 — 클라이언트 상태만 삭제, 확인 불필요 (design §1.3) */}
          <button onClick={clear} aria-label="지우기" title="지우기" className={iconBtn}>
            <Trash2 size={16} />
          </button>
          <button onClick={copyAll} aria-label="전체 복사" title="전체 복사" className={iconBtn}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
          <button
            onClick={() => setPanelState(maximized ? "open" : "maximized")}
            aria-label={maximized ? "복원" : "최대화"}
            title={maximized ? "복원" : "최대화"}
            className={iconBtn}
          >
            {maximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button
            onClick={() => setPanelState("closed")}
            aria-label="닫기"
            title="닫기 (Esc)"
            className={iconBtn}
          >
            <X size={16} />
          </button>
        </span>
      </div>

      {/* 로그 본문 */}
      <div
        ref={bodyRef}
        className="min-h-0 flex-1 overflow-y-auto px-3 py-2"
        style={{ lineHeight: "var(--leading-code)" }}
      >
        {lines.length === 0 ? (
          <p style={{ color: "var(--color-code-comment)" }}>
            아직 실행된 SQL이 없습니다 — 실행 버튼을 누르면 이 세션의 모든 SQL이 여기에 누적됩니다.
          </p>
        ) : (
          lines.map((line) => <LogLine key={line.id} line={line} />)
        )}
      </div>
    </div>
  );
}

export default SqlLogTerminal;
