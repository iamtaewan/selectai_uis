/**
 * AppShell 스텁 — design.md §1.2 (헤더 56px / 사이드 네비 240px / 푸터 상태바).
 * 사이드 네비 = 데모 여정 순서 (준비하기 ①②③ → 시연하기 ④⑤⑥ → 기타).
 * 구현 담당: UI 컴포넌트 에이전트 (커넥션/프로파일 선택기, 건강 신호등, 가드 레일).
 */
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useSqlLogStore } from "../store/sqlLogStore";
import SqlLogTerminal from "./SqlLogTerminal";

const NAV_ITEMS: { to: string; label: string; group: string }[] = [
  { to: "/connections", label: "① 커넥션", group: "준비하기" },
  { to: "/permissions", label: "② 권한 점검", group: "준비하기" },
  { to: "/profiles", label: "③ 프로파일", group: "준비하기" },
  { to: "/playground", label: "④ 플레이그라운드", group: "시연하기" },
  { to: "/chat", label: "⑤ 챗봇", group: "시연하기" },
  { to: "/enrichment", label: "⑥ 증강 비교", group: "시연하기" },
  { to: "/dashboard", label: "대시보드", group: "기타" },
  { to: "/settings", label: "설정", group: "기타" },
];

export function AppShell({ children }: { children?: ReactNode }) {
  const { lines, panelState, setPanelState } = useSqlLogStore();

  return (
    <div className="flex h-screen flex-col">
      {/* 글로벌 헤더 — 브랜드 액센트 + 제품명 + (커넥션/프로파일 선택기 자리) */}
      <header className="flex h-14 items-center gap-3 border-b border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-4">
        <span className="h-6 w-1 rounded bg-[var(--color-brand)]" aria-hidden />
        <h1 className="text-base font-bold">Select AI Demo Studio</h1>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* 사이드 네비 — 데모 여정 순서 */}
        <nav className="w-60 shrink-0 border-r border-[var(--color-neutral-30)] bg-[var(--color-neutral-20)] p-4">
          <ul className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `block rounded-[var(--radius-md)] px-3 py-2 text-sm ${
                      isActive
                        ? "bg-[var(--color-neutral-0)] font-semibold"
                        : "text-[var(--color-neutral-70)]"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* 콘텐츠 + SQL 로그 터미널 도킹 영역 */}
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto p-8">
            <div className="mx-auto max-w-[1280px]">{children ?? <Outlet />}</div>
          </main>
          <SqlLogTerminal />
        </div>
      </div>

      {/* 글로벌 푸터(상태바) — SQL LOG 토글 */}
      <footer className="flex h-7 items-center gap-4 border-t border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-4 text-xs text-[var(--color-neutral-60)]">
        <button
          onClick={() => setPanelState(panelState === "closed" ? "open" : "closed")}
          className={panelState !== "closed" ? "font-semibold text-[var(--color-neutral-90)]" : ""}
        >
          ▣ SQL LOG ({lines.length})
        </button>
        <span className="ml-auto">v0.1.0</span>
      </footer>
    </div>
  );
}

export default AppShell;
