/**
 * 스키마 복제 페이지 — 준비하기 (권한 점검 다음).
 * SH 스키마를 현재 커넥션 user 스키마로 복제(테이블·제약·뷰). 진행 과정은 단계 로그로 표시.
 * SH 읽기 권한이 없으면 사유를 표시하고 복제를 비활성화한다.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getEnvelope, postEnvelope } from "../api/client";
import Button from "../components/Button";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

interface CloneCheck {
  current_user: string;
  source_schema: string;
  has_read: boolean;
  blocked_reason_ko: string | null;
  tables: string[];
  views: string[];
  table_count: number;
  view_count: number;
  key_count: number;
  fk_count: number;
}

interface CloneStep {
  phase: string;
  object: string;
  status: "ok" | "skip" | "error";
  detail: string;
  sql: string | null;
}
interface CloneResult {
  summary: {
    target_schema: string;
    source_schema: string;
    tables_created: number;
    tables_total: number;
    ok: number;
    failed: number;
  };
  steps: CloneStep[];
}

const STATUS_MARK: Record<CloneStep["status"], string> = { ok: "✓", skip: "·", error: "✗" };

export function SchemaClone() {
  const activeConnection = useConnectionStore((s) => s.activeConnection);
  const activeConnectionId = useConnectionStore((s) => s.activeConnectionId);
  const [overwrite, setOverwrite] = useState(true);

  const checkQuery = useQuery({
    queryKey: ["clone", "sh", "check", activeConnectionId],
    enabled: !!activeConnectionId,
    queryFn: async () =>
      (await getEnvelope<CloneCheck>("/clone/sh/check", undefined, { suppressErrorToast: true }))
        .data,
  });
  const check = checkQuery.data;

  const cloneMut = useMutation({
    mutationFn: () =>
      postEnvelope<CloneResult>(
        "/clone/sh/run",
        { overwrite },
        { sqlLogTag: "PG-clone/run" },
      ),
  });
  const result = cloneMut.data?.data;

  if (!activeConnection) {
    return (
      <Panel title="스키마 복제">
        <p className="text-sm text-[var(--color-neutral-60)]">
          먼저 커넥션을 연결하세요.{" "}
          <Link to="/connections" className="text-[var(--color-link)] underline">
            ① 커넥션으로 이동
          </Link>
        </p>
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-bold">스키마 복제</h2>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          데모용 <b>SH</b> 스키마(판매 이력)를 현재 접속 사용자 스키마로 복제합니다 — 테이블·데이터·키/FK
          제약·뷰. SH에 읽기 권한이 있어야 합니다.
        </p>
      </div>

      {/* 권한 점검 + 인벤토리 */}
      <Panel title="① SH 읽기 권한 점검">
        {checkQuery.isFetching && !check ? (
          <p className="text-sm text-[var(--color-running)]">권한 점검 중…</p>
        ) : check ? (
          check.has_read ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <StatusBadge status="success">권한 있음</StatusBadge>
                <span className="text-sm text-[var(--color-neutral-70)]">
                  접속 사용자 <b>{check.current_user}</b> — {check.source_schema} 읽기 가능
                </span>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-[var(--color-neutral-70)]">
                <span className="rounded-[var(--radius-sm)] bg-[var(--color-neutral-20)] px-2 py-1">
                  테이블 {check.table_count}
                </span>
                <span className="rounded-[var(--radius-sm)] bg-[var(--color-neutral-20)] px-2 py-1">
                  뷰 {check.view_count}
                </span>
                <span className="rounded-[var(--radius-sm)] bg-[var(--color-neutral-20)] px-2 py-1">
                  키 제약 {check.key_count}
                </span>
                <span className="rounded-[var(--radius-sm)] bg-[var(--color-neutral-20)] px-2 py-1">
                  FK {check.fk_count}
                </span>
              </div>
              {check.tables.length > 0 ? (
                <p className="font-mono text-xs text-[var(--color-neutral-60)]">
                  {check.tables.join(", ")}
                </p>
              ) : null}
            </div>
          ) : (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-warning)] bg-[var(--color-warning-tint)] p-3">
              <div className="flex items-center gap-2">
                <StatusBadge status="warning">권한 없음</StatusBadge>
                <span className="text-sm font-medium">SH 스키마 읽기 권한이 없습니다</span>
              </div>
              <p className="mt-1 text-sm text-[var(--color-neutral-70)]">
                {check.blocked_reason_ko ??
                  "SH 테이블에 대한 SELECT 권한이 필요합니다. 권한 부여 후 다시 시도하세요."}
              </p>
              <p className="mt-1 text-xs text-[var(--color-neutral-60)]">
                예: <code>GRANT SELECT ANY TABLE TO {check.current_user}</code> 또는 SH 개별 테이블
                SELECT 권한 부여.
              </p>
            </div>
          )
        ) : (
          <p className="text-sm text-[var(--color-danger)]">권한 점검 결과를 불러오지 못했습니다.</p>
        )}
      </Panel>

      {/* 복제 실행 */}
      <Panel title="② 복제 실행">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={overwrite}
              onChange={(e) => setOverwrite(e.target.checked)}
            />
            기존 동명 객체 덮어쓰기 (DROP 후 재생성)
          </label>
          <Button
            loading={cloneMut.isPending}
            disabled={!check?.has_read}
            onClick={() => cloneMut.mutate()}
          >
            복제 실행
          </Button>
          {!check?.has_read ? (
            <span className="text-xs text-[var(--color-neutral-50)]">
              SH 읽기 권한이 없어 복제할 수 없습니다.
            </span>
          ) : null}
        </div>
        {cloneMut.isPending ? (
          <p className="mt-2 text-sm text-[var(--color-running)]">
            복제 중… (SALES 등 대용량 테이블은 수 초 소요될 수 있습니다)
          </p>
        ) : null}
      </Panel>

      {/* 진행 로그 */}
      {result ? (
        <Panel title="③ 진행 로그">
          <div className="mb-3 flex items-center gap-2">
            <StatusBadge status={result.summary.failed === 0 ? "success" : "error"}>
              {result.summary.failed === 0 ? "복제 완료" : "일부 실패"}
            </StatusBadge>
            <span className="text-sm text-[var(--color-neutral-70)]">
              {result.summary.source_schema} → <b>{result.summary.target_schema}</b> · 테이블{" "}
              {result.summary.tables_created}/{result.summary.tables_total} · 성공{" "}
              {result.summary.ok} · 실패 {result.summary.failed}
            </span>
          </div>
          <ol className="flex flex-col gap-1 rounded-[var(--radius-lg)] bg-[var(--color-code-bg)] p-3 font-mono text-xs">
            {result.steps.map((s, i) => (
              <li key={i} className="flex flex-col gap-0.5 border-b border-white/5 pb-1 last:border-0">
                <div className="flex items-center gap-2">
                  <span
                    style={{
                      color:
                        s.status === "error"
                          ? "var(--color-danger)"
                          : s.status === "skip"
                            ? "var(--color-code-comment)"
                            : "var(--color-code-string)",
                    }}
                  >
                    {STATUS_MARK[s.status]}
                  </span>
                  <span className="text-[var(--color-code-comment)]">[{s.phase}]</span>
                  <span className="text-[var(--color-code-text)]">{s.object}</span>
                  <span className="text-[var(--color-code-comment)]">— {s.detail}</span>
                </div>
                {s.sql ? (
                  <code className="pl-5 text-[var(--color-code-keyword)]">{s.sql}</code>
                ) : null}
              </li>
            ))}
          </ol>
        </Panel>
      ) : null}
    </div>
  );
}

export default SchemaClone;
