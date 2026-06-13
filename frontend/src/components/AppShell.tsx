/**
 * AppShell — design.md §1.2 글로벌 셸 (헤더 56px / 사이드 네비 240px / 글로벌 푸터 상태바).
 *
 * - 헤더: 브랜드 액센트 + 제품명 / 커넥션 선택기(상태 점) / 기본 프로파일 선택기 / 건강 신호등
 * - 사이드바: 데모 여정 순서(준비하기 ①②③ → 시연하기 ④⑤⑥ → 기타).
 *   가드 레일 — 커넥션 없으면 ②~⑥ 잠금(자물쇠 + 툴팁 + 클릭 시 ①로 유도)
 * - 푸터(상태바): SQL 투명 모드 토글 / ▣ SQL LOG (n) 토글(§5.9) / 단순|전문가 전환
 * - 콘텐츠: <Outlet/> + SqlLogTerminal 도킹 — PG-00(/)·PG-08(/settings) 제외 (design §1.3)
 * - 건강 황/적이면 시연 메뉴(④⑤⑥) 진입 시 황색 경고 배너 + 원클릭 이동 (design §1.2)
 */
import { useEffect, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Lock } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { getEnvelope, putEnvelope } from "../api/client";
import type { ConnectionOut, DashboardHealth, ProfileSummary, SignalStatus } from "../api/types";
import { useConnectionStore } from "../store/connectionStore";
import { useSqlLogStore } from "../store/sqlLogStore";
import SqlLogTerminal from "./SqlLogTerminal";
import { ToastContainer } from "./Toast";

// ---------------------------------------------------------------- 내비게이션 정의

interface NavItem {
  to: string;
  /** 여정 순번 (①~⑥) — 기타 그룹은 없음 */
  step?: string;
  label: string;
  group: "준비하기" | "시연하기" | "기타";
  /** true면 커넥션 없을 때 잠금 (가드 레일 — ②~⑥) */
  requiresConnection: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/connections", step: "①", label: "커넥션", group: "준비하기", requiresConnection: false },
  { to: "/permissions", step: "②", label: "권한 점검", group: "준비하기", requiresConnection: true },
  { to: "/profiles", step: "③", label: "프로파일", group: "준비하기", requiresConnection: true },
  { to: "/playground", step: "④", label: "플레이그라운드", group: "시연하기", requiresConnection: true },
  { to: "/chat", step: "⑤", label: "챗봇", group: "시연하기", requiresConnection: true },
  { to: "/enrichment", step: "⑥", label: "증강 비교", group: "시연하기", requiresConnection: true },
  { to: "/dashboard", label: "대시보드", group: "기타", requiresConnection: false },
  { to: "/settings", label: "설정", group: "기타", requiresConnection: false },
];

const NAV_GROUPS: NavItem["group"][] = ["준비하기", "시연하기", "기타"];

/** SqlLogTerminal을 도킹하지 않는 경로 — PG-00 온보딩, PG-08 설정 (design §1.3) */
const NO_TERMINAL_PATHS = ["/", "/settings"];

/** 건강 황/적 경고 배너를 띄우는 시연 경로 (④⑤⑥) */
const DEMO_PATHS = ["/playground", "/chat", "/enrichment"];

const SIGNAL_COLOR: Record<SignalStatus, string> = {
  green: "var(--color-success)",
  yellow: "var(--color-warning)",
  red: "var(--color-danger)",
};

// ---------------------------------------------------------------- 셸 본체

export function AppShell({ children }: { children?: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const sqlLogCount = useSqlLogStore((s) => s.lines.length);
  const panelState = useSqlLogStore((s) => s.panelState);
  const togglePanel = useSqlLogStore((s) => s.togglePanel);

  const {
    activeConnection,
    activeConnectionId,
    defaultProfileName,
    mode,
    sqlTransparent,
    setActiveConnection,
    setDefaultProfileName,
    setMode,
    toggleSqlTransparent,
  } = useConnectionStore();

  // ---- 셸 데이터 (백그라운드 — 오류 토스트 생략, 실패 시 빈 상태로 우아하게)
  const connectionsQuery = useQuery({
    queryKey: ["connections"],
    queryFn: () =>
      getEnvelope<ConnectionOut[]>("/connections", undefined, { suppressErrorToast: true }),
  });
  const connections = connectionsQuery.data?.data ?? [];

  const profilesQuery = useQuery({
    queryKey: ["profiles", activeConnectionId],
    enabled: !!activeConnectionId,
    queryFn: () =>
      getEnvelope<ProfileSummary[]>("/profiles", undefined, { suppressErrorToast: true }),
  });
  const profiles = profilesQuery.data?.data ?? [];

  const healthQuery = useQuery({
    queryKey: ["dashboard", "health", activeConnectionId],
    enabled: !!activeConnectionId,
    // 서버 측 30초 캐시(api-spec §9.1)에 맞춰 보수적으로 폴링
    refetchInterval: 60_000,
    queryFn: () =>
      getEnvelope<DashboardHealth>("/dashboard/health", undefined, { suppressErrorToast: true }),
  });
  const health = healthQuery.data?.data ?? null;

  // 마지막 사용 커넥션 자동 선택 — 서버가 last_used_at 내림차순 정렬 (FR-02)
  useEffect(() => {
    if (!activeConnectionId && connections.length > 0) {
      setActiveConnection(connections[0]);
    }
  }, [activeConnectionId, connections, setActiveConnection]);

  // 서버 설정의 기본 프로파일(is_default)을 스토어로 동기화
  useEffect(() => {
    const serverDefault = profiles.find((p) => p.is_default);
    if (serverDefault && !defaultProfileName) {
      setDefaultProfileName(serverDefault.profile_name);
    }
  }, [profiles, defaultProfileName, setDefaultProfileName]);

  // ---- 파생 상태
  const showTerminal = !NO_TERMINAL_PATHS.includes(location.pathname);
  const isDemoPath = DEMO_PATHS.some((p) => location.pathname.startsWith(p));
  const badSignals = health?.signals.filter((s) => s.status !== "green") ?? [];
  const showHealthBanner = isDemoPath && health != null && health.overall !== "green";

  /** 여정 단계 완료(✓) 판정 — 건강 신호 우선, 없으면 로컬 상태로 보수 판정 */
  const stepDone = (item: NavItem): boolean => {
    const signal = (id: string) => health?.signals.find((s) => s.id === id)?.status;
    switch (item.to) {
      case "/connections":
        return !!activeConnection;
      case "/permissions":
        return signal("privileges") === "green";
      case "/profiles":
        return signal("default_profile") === "green" || !!defaultProfileName;
      default:
        return false;
    }
  };

  const onSelectConnection = (id: string) => {
    setActiveConnection(connections.find((c) => c.id === id) ?? null);
  };

  const onSelectProfile = (profileName: string) => {
    setDefaultProfileName(profileName || null);
    if (!profileName) return;
    // 앱 수준 기본 프로파일 = 서버 settings.json (api-spec §4.8) — 즉시 저장
    putEnvelope("/settings/default-profile", { profile_name: profileName })
      .then(() => queryClient.invalidateQueries({ queryKey: ["profiles"] }))
      .catch(() => {
        /* 오류 토스트는 인터셉터가 표시 */
      });
  };

  const connDotColor =
    activeConnection == null
      ? "var(--color-neutral-50)"
      : activeConnection.status === "INVALID"
        ? "var(--color-danger)"
        : "var(--color-success)";

  const greenCount = health ? health.signals.filter((s) => s.status === "green").length : 0;

  return (
    <div className="flex h-screen flex-col bg-[var(--color-neutral-10)]">
      {/* ============ 글로벌 헤더 56px — 브랜드 / 커넥션·프로파일 선택기 / 건강 신호등 ============ */}
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-4">
        <span className="h-6 w-1 rounded bg-[var(--color-brand)]" aria-hidden />
        <h1 className="text-base font-bold tracking-tight">Select AI Demo Studio</h1>

        <div className="ml-auto flex items-center gap-2">
          {/* 커넥션 선택기 + 연결 상태 점 (FR-02 마지막 사용 자동 선택) */}
          <label className="flex h-9 items-center gap-2 rounded-full border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-3">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: connDotColor }}
              aria-hidden
            />
            <span className="sr-only">활성 커넥션</span>
            {connections.length === 0 ? (
              <NavLink to="/connections" className="text-sm text-[var(--color-link)]">
                커넥션 없음 — 연결하기
              </NavLink>
            ) : (
              <select
                value={activeConnectionId ?? ""}
                onChange={(e) => onSelectConnection(e.target.value)}
                className="max-w-44 bg-transparent text-sm font-medium outline-none"
                aria-label="활성 커넥션 선택"
              >
                {connections.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} / {c.username}
                  </option>
                ))}
              </select>
            )}
          </label>

          {/* 기본 프로파일 선택기 — 앱 설정, 매 호출 profile_name 명시 전달 (설계 전제 3) */}
          <label className="flex h-9 items-center gap-2 rounded-full border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-3">
            <span className="text-xs text-[var(--color-neutral-60)]">기본 프로파일</span>
            {profiles.length === 0 ? (
              <span className="text-sm text-[var(--color-neutral-50)]">
                {defaultProfileName ?? "없음"}
              </span>
            ) : (
              <select
                value={defaultProfileName ?? ""}
                onChange={(e) => onSelectProfile(e.target.value)}
                className="max-w-40 bg-transparent text-sm font-medium outline-none"
                aria-label="기본 프로파일 선택"
              >
                {defaultProfileName == null ? <option value="">선택…</option> : null}
                {profiles.map((p) => (
                  <option key={p.profile_name} value={p.profile_name}>
                    {p.profile_name}
                  </option>
                ))}
              </select>
            )}
          </label>

          {/* 건강 신호등 — 클릭 시 대시보드 이동 (FR-09 요약 점) */}
          <button
            onClick={() => navigate("/dashboard")}
            className="flex h-9 items-center gap-2 rounded-full border border-[var(--color-neutral-30)] px-3 text-sm hover:bg-[var(--color-neutral-20)]"
            title={
              health
                ? health.signals.map((s) => `${s.title_ko}: ${s.detail_ko}`).join("\n")
                : "건강 점검 결과 없음 — 대시보드에서 점검"
            }
            aria-label="건강 신호등 — 대시보드로 이동"
          >
            <span
              className="h-3 w-3 rounded-full"
              style={{
                background: health ? SIGNAL_COLOR[health.overall] : "var(--color-neutral-40)",
              }}
              aria-hidden
            />
            {health ? (
              <span className="font-medium">
                건강 {greenCount}/{health.signals.length} 통과
              </span>
            ) : (
              <span className="text-[var(--color-neutral-60)]">건강 미점검</span>
            )}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* ============ 사이드 네비 240px — 데모 여정 순서 + 가드 레일 ============ */}
        <nav className="w-60 shrink-0 overflow-y-auto border-r border-[var(--color-neutral-30)] bg-[var(--color-neutral-20)] p-4">
          {NAV_GROUPS.map((group) => (
            <div key={group} className="mb-4">
              <p className="mb-1 px-3 text-xs font-semibold tracking-[0.08em] text-[var(--color-neutral-60)]">
                {group}
              </p>
              <ul className="flex flex-col gap-0.5">
                {NAV_ITEMS.filter((item) => item.group === group).map((item) => {
                  const locked = item.requiresConnection && !activeConnectionId;
                  const done = stepDone(item);
                  if (locked) {
                    return (
                      <li key={item.to}>
                        {/* 잠금 — 비활성 + 자물쇠 + 툴팁, 클릭 시 ①로 유도 (design §1.2 가드 레일) */}
                        <button
                          onClick={() => navigate("/connections")}
                          title="먼저 커넥션을 연결하세요"
                          aria-disabled
                          className="flex w-full cursor-not-allowed items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-left text-sm text-[var(--color-neutral-50)]"
                        >
                          <span className="w-4">{item.step}</span>
                          <span className="flex-1">{item.label}</span>
                          <Lock size={14} aria-label="잠김" />
                        </button>
                      </li>
                    );
                  }
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        className={({ isActive }) =>
                          `flex items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-sm ${
                            isActive
                              ? "bg-[var(--color-neutral-0)] font-semibold text-[var(--color-neutral-90)] shadow-sm"
                              : "text-[var(--color-neutral-70)] hover:bg-[var(--color-neutral-0)]"
                          }`
                        }
                      >
                        <span className="w-4">{item.step}</span>
                        <span className="flex-1">{item.label}</span>
                        {done ? (
                          <span className="text-[var(--color-success)]" aria-label="완료">
                            ✓
                          </span>
                        ) : null}
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* ============ 콘텐츠 + SqlLogTerminal 도킹 영역 ============ */}
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto p-8">
            <div className="mx-auto max-w-[1280px]">
              {/* 건강 황/적 — 시연 화면(④⑤⑥) 상단 황색 경고 배너 (design §1.2) */}
              {showHealthBanner ? (
                <div
                  role="alert"
                  className="mb-5 flex items-center gap-3 rounded-[var(--radius-lg)] bg-[var(--color-warning-tint)] px-4 py-3 text-sm text-[var(--color-warning)]"
                >
                  <Activity size={16} aria-hidden />
                  <span className="flex-1 font-medium">
                    권한/환경 점검 미통과 항목 {badSignals.length}건 — 데모 중 오류가 발생할 수
                    있습니다.
                  </span>
                  <button
                    onClick={() => navigate("/dashboard")}
                    className="shrink-0 rounded-[var(--radius-md)] border border-[var(--color-warning)] px-3 py-1 font-semibold hover:bg-[var(--color-warning)] hover:text-[var(--color-neutral-0)]"
                  >
                    대시보드에서 확인
                  </button>
                </div>
              ) : null}
              {children ?? <Outlet />}
            </div>
          </main>
          {/* PG-00·PG-08 제외 도킹 (design §1.3) — 로그 자체는 전역 스토어라 페이지 이동에도 유지 */}
          {showTerminal ? <SqlLogTerminal /> : null}
        </div>
      </div>

      {/* ============ 글로벌 푸터(상태바) — SQL 투명 모드 / SQL LOG / 단순|전문가 ============ */}
      <footer className="flex h-7 shrink-0 items-stretch gap-1 border-t border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] px-3 text-xs">
        {/* SQL 투명 모드 — 각 화면 인라인 SQL 펼침 기본 상태 제어 (SqlLogTerminal과 독립) */}
        <button
          onClick={toggleSqlTransparent}
          className="flex items-center gap-1 px-2 text-[var(--color-neutral-60)] hover:bg-[var(--color-neutral-20)]"
          aria-pressed={sqlTransparent}
          title="각 화면의 SQL 미리보기/펼침 기본 상태를 제어합니다"
        >
          SQL 투명 모드
          <b
            style={{
              color: sqlTransparent ? "var(--color-brand)" : "var(--color-neutral-50)",
            }}
          >
            {sqlTransparent ? "켜짐" : "꺼짐"}
          </b>
        </button>

        {/* ▣ SQL LOG (n) — 열림 시 상단 2px 브랜드 인디케이터 (style §5.9 상태바 토글) */}
        <button
          onClick={togglePanel}
          className="flex items-center gap-1 px-2 hover:bg-[var(--color-neutral-20)]"
          style={
            panelState !== "closed"
              ? {
                  color: "var(--color-neutral-90)",
                  fontWeight: 600,
                  boxShadow: "inset 0 2px 0 var(--color-brand)",
                }
              : { color: "var(--color-neutral-60)" }
          }
          aria-pressed={panelState !== "closed"}
          title="SQL 로그 터미널 열기/닫기 (Ctrl/Cmd + `)"
        >
          ▣ SQL LOG ({sqlLogCount})
        </button>

        {/* 단순|전문가 모드 전환 (design §1.2 — 푸터) */}
        <span className="ml-2 flex items-center gap-1 text-[var(--color-neutral-60)]">
          {(["simple", "expert"] as const).map((m, i) => (
            <span key={m} className="flex items-center gap-1">
              {i > 0 ? <span aria-hidden>|</span> : null}
              <button
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
                className={
                  mode === m
                    ? "font-semibold text-[var(--color-neutral-90)]"
                    : "hover:text-[var(--color-neutral-90)]"
                }
              >
                {m === "simple" ? "단순" : "전문가"}
              </button>
            </span>
          ))}
        </span>

        <span className="ml-auto flex items-center text-[var(--color-neutral-50)]">v0.1.0</span>
      </footer>

      {/* 전역 토스트 렌더러 — 1인스턴스 (style §5.8) */}
      <ToastContainer />
    </div>
  );
}

export default AppShell;
