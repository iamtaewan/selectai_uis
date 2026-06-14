/**
 * Dashboard 페이지 — PG-07 (/dashboard) / FR-09 (P1).
 * 데모 상태 신호등 — 커넥션/권한/Data Access/기본 프로파일/데모 스키마 일괄 점검.
 * 근거: design.md §3 PG-07, api-spec §9.1 (GET /dashboard/health — 캐시 30초).
 * - 신호등 3색(green/yellow/red) + 행별 해당 화면 딥링크 (전체 차단 없음)
 * - fix_endpoint: enrichment/demo-schema는 즉시 실행 버튼, 그 외(권한 등 입력 필요한 조치)는
 *   해당 점검 화면으로 딥링크 — 합리적 가정 (privileges/apply는 credential 입력이 필요해
 *   대시보드에서 무인자 실행이 불가능하다는 판단, 주석으로 명시)
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getEnvelope, postEnvelope } from "../api/client";
import type { DashboardHealth, HealthSignal, SignalStatus } from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";

/** 신호등 점 색상 — style.md 상태 토큰 매핑 */
const DOT_COLOR: Record<SignalStatus, string> = {
  green: "var(--color-success)",
  yellow: "var(--color-warning)",
  red: "var(--color-danger)",
};

/** 종합 상태 한 줄 요약 문구 */
const OVERALL_LABEL: Record<SignalStatus, string> = {
  green: "시연 가능 — 모든 점검 통과",
  yellow: "시연 가능 (일부 데모만 준비 필요)",
  red: "시연 불가 — 적색 항목을 먼저 해결하세요",
};

/** 신호 id → 관련 점검/관리 화면 딥링크 (design.md PG-07 — 각 행에 해당 화면 딥링크) */
const SIGNAL_LINKS: Record<string, { to: string; label: string }> = {
  connection: { to: "/connections", label: "관리" },
  privileges: { to: "/permissions", label: "보기" },
  data_access: { to: "/permissions", label: "보기" },
  default_profile: { to: "/settings", label: "보기" },
  demo_schema: { to: "/enrichment", label: "보기" },
};

/** 신호등 점 — 점 + 상태별 색 */
function SignalDot({ status }: { status: SignalStatus }) {
  return (
    <span
      aria-label={status}
      className="inline-block h-3.5 w-3.5 shrink-0 rounded-full"
      style={{ background: DOT_COLOR[status] }}
    />
  );
}

export function Dashboard() {
  const pushToast = useToastStore((s) => s.push);

  // 건강 점검 — 백엔드 캐시 30초 (api-spec §9.1), 헤더 건강 점과 동일 데이터
  const healthQuery = useQuery({
    queryKey: ["dashboard", "health"],
    queryFn: () =>
      getEnvelope<DashboardHealth>("/dashboard/health", undefined, {
        suppressErrorToast: true,
      }),
    staleTime: 30_000,
  });

  // fix_endpoint 즉시 실행 — 무인자 POST가 가능한 조치만 (현재: 데모 스키마 생성)
  const fixMutation = useMutation({
    mutationFn: (signal: HealthSignal) => {
      // "POST /api/v1/enrichment/demo-schema" → baseURL(/api/v1) 기준 상대 경로로 변환
      const path = (signal.fix_endpoint ?? "").replace(/^POST\s+/i, "").replace(/^\/api\/v1/, "");
      return postEnvelope<unknown>(path, {}, { sqlLogTag: `PG-07/fix:${signal.id}` });
    },
    onSuccess: (_envelope, signal) => {
      pushToast({ status: "success", title: `조치 완료 — ${signal.title_ko}` });
      void healthQuery.refetch();
    },
  });

  /** 대시보드에서 즉시 실행 가능한 fix인지 판단 — credential 등 입력이 필요한 조치는 딥링크로 */
  const isDirectlyFixable = (signal: HealthSignal): boolean =>
    Boolean(signal.fix_endpoint && signal.fix_endpoint.includes("/enrichment/demo-schema"));

  const health = healthQuery.data?.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">데모 상태</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            데모 직전 30초 — 지금 시연 가능한지 한 화면에서 확인합니다.
          </p>
        </div>
        <Button
          variant="secondary"
          loading={healthQuery.isFetching}
          onClick={() => void healthQuery.refetch()}
        >
          전체 재점검 ↻
        </Button>
      </div>

      <Panel className="p-0">
        {healthQuery.isPending ? (
          <div className="flex flex-col gap-3 p-6">
            {/* 로딩 — 행별 순차 점검 느낌의 스켈레톤 */}
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex animate-pulse items-center gap-3">
                <span className="h-3.5 w-3.5 rounded-full bg-[var(--color-neutral-30)]" />
                <span className="h-4 w-2/3 rounded bg-[var(--color-neutral-20)]" />
              </div>
            ))}
            <p className="text-sm text-[var(--color-neutral-60)]">◌ 항목별 점검 중…</p>
          </div>
        ) : healthQuery.error ? (
          <div className="p-6">
            <StatusBadge status="error">점검 불가</StatusBadge>
            <p className="mt-2 text-sm text-[var(--color-neutral-70)]">
              건강 점검 API 호출에 실패했습니다 — 커넥션 상태를 확인하세요.
            </p>
            <div className="mt-3 flex gap-2">
              <Button variant="secondary" onClick={() => void healthQuery.refetch()}>
                재시도
              </Button>
              <Link to="/connections">
                <Button variant="ghost">커넥션 관리 →</Button>
              </Link>
            </div>
          </div>
        ) : health ? (
          <ul>
            {health.signals.map((signal) => {
              const link = SIGNAL_LINKS[signal.id];
              return (
                <li
                  key={signal.id}
                  className="flex items-center gap-3 border-b border-[var(--color-neutral-30)] px-6 py-4 last:border-b-0"
                >
                  <SignalDot status={signal.status} />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{signal.title_ko}</p>
                    <p className="truncate text-sm text-[var(--color-neutral-60)]">
                      {signal.detail_ko}
                    </p>
                  </div>
                  {signal.fix_endpoint && isDirectlyFixable(signal) ? (
                    <Button
                      variant="secondary"
                      loading={fixMutation.isPending && fixMutation.variables?.id === signal.id}
                      onClick={() => fixMutation.mutate(signal)}
                      title={signal.fix_endpoint}
                    >
                      생성
                    </Button>
                  ) : null}
                  {signal.fix_endpoint && !isDirectlyFixable(signal) && link ? (
                    <Link to={link.to}>
                      <Button variant="secondary" title={signal.fix_endpoint}>
                        조치하러 가기
                      </Button>
                    </Link>
                  ) : null}
                  {link ? (
                    <Link to={link.to} className="text-sm text-[var(--color-link)]">
                      {link.label} →
                    </Link>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : null}

        {/* 종합 신호 + 시연 화면 바로가기 */}
        {health ? (
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--color-neutral-10)] px-6 py-4">
            <div className="flex items-center gap-2">
              <SignalDot status={health.overall} />
              <span className="font-semibold">종합: {OVERALL_LABEL[health.overall]}</span>
            </div>
            <div className="flex gap-2">
              <Link to="/playground">
                <Button variant="ghost">플레이그라운드로 →</Button>
              </Link>
              <Link to="/chat">
                <Button variant="ghost">챗봇으로 →</Button>
              </Link>
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel variant="explain">
        ⓘ 이 신호등은 헤더의 건강 점과 동일한 데이터(GET /dashboard/health, 30초 캐시)입니다. 행
        단위로 점검이 실패해도 다른 항목 점검은 계속됩니다 — 전체 차단 없음.
      </Panel>
    </div>
  );
}

export default Dashboard;
