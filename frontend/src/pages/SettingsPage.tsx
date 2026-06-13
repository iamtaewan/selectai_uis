/**
 * SettingsPage 페이지 — PG-08 (/settings) / FR-05, FR-10, 공통.
 * 4개 섹션:
 *   1. 기본 프로파일 (앱 설정 — GET/PUT /settings/default-profile, 세션 SET_PROFILE 미사용)
 *   2. 표시 모드 (단순/전문가, SQL 투명 모드) — localStorage (connectionStore, X4 결정)
 *   3. 데모 스키마 관리 (생성/리셋/삭제)
 *   4. 데모 환경 정리 — 생성 리소스 대장(resources.json) 기반, 실행 전 미리보기+확인 (FR-10)
 * 근거: design.md §3 PG-08, api-spec §10(resources)·settings/default-profile.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteEnvelope, getEnvelope, postEnvelope, putEnvelope } from "../api/client";
import type {
  CleanupItemResult,
  CleanupListResult,
  CleanupResult,
  DefaultProfileSetting,
  ProfileSummary,
} from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";
import { useConnectionStore } from "../store/connectionStore";

export function SettingsPage() {
  const pushToast = useToastStore((s) => s.push);
  const queryClient = useQueryClient();
  const mode = useConnectionStore((s) => s.mode);
  const setMode = useConnectionStore((s) => s.setMode);
  const sqlTransparent = useConnectionStore((s) => s.sqlTransparent);
  const toggleSqlTransparent = useConnectionStore((s) => s.toggleSqlTransparent);
  const setDefaultProfileName = useConnectionStore((s) => s.setDefaultProfileName);

  const [cleanupPreview, setCleanupPreview] = useState<CleanupItemResult[] | null>(null);

  // ── 1. 기본 프로파일 ──────────────────────────
  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: () => getEnvelope<ProfileSummary[]>("/profiles", undefined, { suppressErrorToast: true }),
  });
  const defaultQuery = useQuery({
    queryKey: ["settings", "default-profile"],
    queryFn: () =>
      getEnvelope<DefaultProfileSetting>("/settings/default-profile", undefined, {
        suppressErrorToast: true,
      }),
  });
  const setDefault = useMutation({
    mutationFn: (profileName: string) =>
      putEnvelope<DefaultProfileSetting>("/settings/default-profile", { profile_name: profileName }),
    onSuccess: (env) => {
      setDefaultProfileName(env.data.profile_name);
      pushToast({ status: "success", title: `기본 프로파일 → ${env.data.profile_name}` });
      void defaultQuery.refetch();
    },
  });

  // ── 3. 데모 스키마 관리 ──────────────────────────
  const createDemo = useMutation({
    mutationFn: () =>
      postEnvelope("/enrichment/demo-schema", { reset: false }, { sqlLogTag: "PG-08/스키마생성" }),
    onSuccess: () => pushToast({ status: "success", title: "데모 스키마 생성 완료" }),
  });
  const resetDemo = useMutation({
    mutationFn: () =>
      postEnvelope("/enrichment/demo-schema", { reset: true }, { sqlLogTag: "PG-08/스키마리셋" }),
    onSuccess: () => pushToast({ status: "success", title: "데모 스키마 초기화 완료" }),
  });
  const dropDemo = useMutation({
    mutationFn: () => deleteEnvelope("/enrichment/demo-schema", { sqlLogTag: "PG-08/스키마삭제" }),
    onSuccess: () => pushToast({ status: "success", title: "데모 스키마 삭제 완료" }),
  });

  // ── 4. 데모 환경 정리 (리소스 대장) ──────────────────────────
  const resourcesQuery = useQuery({
    queryKey: ["resources"],
    queryFn: () =>
      getEnvelope<CleanupListResult>("/resources", { status: "pending" }, { suppressErrorToast: true }),
  });

  // dry_run으로 정리 예정 SQL 미리보기
  const previewCleanup = useMutation({
    mutationFn: () =>
      postEnvelope<CleanupResult>("/resources/cleanup", { dry_run: true }, { suppressErrorToast: true }),
    onSuccess: (env) => setCleanupPreview(env.data.results),
  });

  // 실제 일괄 정리 실행
  const runCleanup = useMutation({
    mutationFn: () =>
      postEnvelope<CleanupResult>(
        "/resources/cleanup",
        { dry_run: false, include_app_files: true },
        { sqlLogTag: "PG-08/일괄정리" },
      ),
    onSuccess: (env) => {
      const done = env.data.summary.done ?? 0;
      const failed = env.data.summary.failed ?? 0;
      pushToast({
        status: failed > 0 ? "warning" : "success",
        title: `정리 완료 — 성공 ${done}, 실패 ${failed}`,
      });
      setCleanupPreview(null);
      void resourcesQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });

  // 개별 리소스 정리
  const deleteResource = useMutation({
    mutationFn: (id: string) =>
      deleteEnvelope<CleanupItemResult>(`/resources/${id}`, { sqlLogTag: `PG-08/정리:${id}` }),
    onSuccess: () => {
      pushToast({ status: "success", title: "개별 리소스 정리 완료" });
      void resourcesQuery.refetch();
    },
  });

  const profiles = profilesQuery.data?.data ?? [];
  const currentDefault = defaultQuery.data?.data.profile_name ?? null;
  const ledgerItems = resourcesQuery.data?.data.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-bold">앱 설정</h2>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          기본 프로파일, 표시 모드, 데모 스키마/리소스 정리.
        </p>
      </div>

      {/* 1. 기본 프로파일 */}
      <Panel title="기본 프로파일 (앱 설정)">
        <p className="mb-3 text-sm text-[var(--color-neutral-70)]">
          DB 세션에 SET_PROFILE을 걸지 않습니다. 여기서 고른 값이 매 Select AI 호출에{" "}
          <code>profile_name</code>으로 전달됩니다.
        </p>
        {profilesQuery.isPending ? (
          <p className="text-sm text-[var(--color-neutral-60)]">프로파일 목록 로딩 중…</p>
        ) : profiles.length === 0 ? (
          <p className="text-sm text-[var(--color-neutral-60)]">
            저장된 프로파일이 없습니다 — 프로파일 화면에서 먼저 생성하세요.
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="rounded-[var(--radius-md)] border border-[var(--color-neutral-40)] px-3 py-2 text-sm"
              value={currentDefault ?? ""}
              onChange={(e) => setDefault.mutate(e.target.value)}
            >
              <option value="" disabled>
                기본 프로파일 선택…
              </option>
              {profiles.map((p) => (
                <option key={p.profile_name} value={p.profile_name}>
                  {p.profile_name} {p.is_default ? "★" : ""}
                </option>
              ))}
            </select>
            {currentDefault ? <StatusBadge status="success">현재: {currentDefault}</StatusBadge> : null}
          </div>
        )}
      </Panel>

      {/* 2. 표시 모드 */}
      <Panel title="표시 모드 (이 브라우저에만 저장)">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="w-32 text-sm">데모 모드</span>
            <Button
              variant={mode === "simple" ? "primary" : "secondary"}
              onClick={() => setMode("simple")}
            >
              단순 (영업)
            </Button>
            <Button
              variant={mode === "expert" ? "primary" : "secondary"}
              onClick={() => setMode("expert")}
            >
              전문가 (Presales/파트너)
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-32 text-sm">SQL 투명 모드</span>
            <Button variant="secondary" onClick={() => toggleSqlTransparent()}>
              {sqlTransparent ? "켜짐 — 인라인 SQL 펼침" : "꺼짐 — 인라인 SQL 접힘"}
            </Button>
          </div>
        </div>
      </Panel>

      {/* 3. 데모 스키마 관리 */}
      <Panel title="데모 스키마 관리 (증강 비교용 무비 스키마)">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" loading={createDemo.isPending} onClick={() => createDemo.mutate()}>
            생성
          </Button>
          <Button variant="secondary" loading={resetDemo.isPending} onClick={() => resetDemo.mutate()}>
            초기화 (COMMENT 제거 후 재생성)
          </Button>
          <Button variant="danger" loading={dropDemo.isPending} onClick={() => dropDemo.mutate()}>
            삭제
          </Button>
        </div>
      </Panel>

      {/* 4. 데모 환경 정리 */}
      <Panel title="데모 환경 정리 — 생성 리소스 대장 (FR-10)">
        <p className="mb-3 text-sm text-[var(--color-neutral-70)]">
          이 도구가 고객 DB에 만든 프로파일/credential/대화/데모 테이블 등을 기록해 두었다가 한 번에
          정리합니다. 실행 전 SQL 미리보기와 확인을 반드시 거칩니다.
        </p>

        {resourcesQuery.isPending ? (
          <p className="text-sm text-[var(--color-neutral-60)]">대장 로딩 중…</p>
        ) : ledgerItems.length === 0 ? (
          <p className="text-sm text-[var(--color-neutral-60)]">정리할 리소스가 없습니다.</p>
        ) : (
          <ul className="mb-3 flex flex-col gap-1">
            {ledgerItems.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-3 border-b border-[var(--color-neutral-20)] py-2 last:border-b-0"
              >
                <StatusBadge status="neutral">{item.resource_type}</StatusBadge>
                <span className="flex-1 truncate font-mono text-sm">{item.resource_name}</span>
                <Button
                  variant="ghost"
                  loading={deleteResource.isPending && deleteResource.variables === item.id}
                  onClick={() => deleteResource.mutate(item.id)}
                >
                  개별 정리
                </Button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            loading={previewCleanup.isPending}
            disabled={ledgerItems.length === 0}
            onClick={() => previewCleanup.mutate()}
          >
            정리 미리보기 (dry-run)
          </Button>
          {cleanupPreview ? (
            <Button variant="danger" loading={runCleanup.isPending} onClick={() => runCleanup.mutate()}>
              전체 정리 실행 ({cleanupPreview.length}건)
            </Button>
          ) : null}
        </div>

        {cleanupPreview ? (
          <div className="mt-3">
            <p className="mb-2 text-sm font-semibold">실행 예정 작업:</p>
            <SqlBlock
              sql={cleanupPreview.map(
                (r) => `-- ${r.resource_type} ${r.resource_name}\n${r.cleanup_action ?? ""}`,
              )}
              label="정리 SQL/작업 미리보기"
              preview
              defaultOpen
            />
          </div>
        ) : null}
      </Panel>
    </div>
  );
}

export default SettingsPage;
