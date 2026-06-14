/**
 * Enrichment 페이지 — PG-06 (/enrichment) / FR-08.
 * Comment 증강 전/후 비교 — 데모의 클라이맥스. 5단계 stepper:
 *   ① 모호 스키마(c1~c7) 원클릭 생성 → ② comments off/on 프로파일 쌍 생성
 *   → ③ COMMENT 편집·적용 → ④ 비교 질문 입력 → ⑤ 좌우 비교(전/후 SQL diff)
 * 근거: design.md §3 PG-06, api-spec §7, selectai-reference §7 (모호 무비 스키마).
 * 모든 실행성 호출은 sqlLogTag를 달아 SqlLogTerminal에 누적된다.
 */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { deleteEnvelope, getEnvelope, postEnvelope, putEnvelope } from "../api/client";
import type {
  CommentEntry,
  EnrichCompareResult,
  EnrichCompareSide,
  ObjectRef,
  SchemaOwnersResult,
} from "../api/types";
import Button from "../components/Button";
import ComparePanes from "../components/ComparePanes";
import Panel from "../components/Panel";
import ResultGrid from "../components/ResultGrid";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";

const PROFILE_OFF = "ENRICH_DEMO_OFF";
const PROFILE_ON = "ENRICH_DEMO_ON";
const DEMO_TABLES = ["TABLE1", "TABLE2", "TABLE3"];

// 응답 보조 타입 (types.ts에 없는 엔드포인트 한정) — api-spec §7 기준
interface DemoSchemaResult {
  tables: string[];
  seeded_rows?: Record<string, number> | number | null;
}
interface CommentColumn {
  column_name: string;
  data_type: string;
  comment: string | null;
}
interface CommentTable {
  owner: string;
  table_name: string;
  comment: string | null;
  columns: CommentColumn[];
}
interface CommentsResult {
  owner: string;
  tables: CommentTable[];
}
interface ProfilePairResult {
  profile_off: string;
  profile_on: string;
}

const STEPS = [
  "① 모호 스키마 생성",
  "② 프로파일 쌍",
  "③ COMMENT 적용",
  "④ 비교 질문",
  "⑤ 전/후 비교",
];

/** 비교 한쪽 결과 렌더 — 생성 SQL + 결과 그리드 또는 오류 */
function ComparePane({ side }: { side: EnrichCompareSide }) {
  if (side.error) {
    return (
      <div className="flex flex-col gap-2">
        <StatusBadge status="error">실행 실패 — {side.error.code}</StatusBadge>
        <p className="text-sm text-[var(--color-neutral-70)]">{side.error.message_ko}</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {side.generated_sql ? (
        <SqlBlock sql={side.generated_sql} label="생성된 SQL 보기" defaultOpen />
      ) : (
        <p className="text-sm text-[var(--color-neutral-60)]">생성된 SQL 없음</p>
      )}
      {side.columns && side.rows ? (
        <ResultGrid columns={side.columns} rows={side.rows} />
      ) : null}
    </div>
  );
}

export function Enrichment() {
  const pushToast = useToastStore((s) => s.push);
  const [step, setStep] = useState(0);
  const [prompt, setPrompt] = useState("총 시청 횟수가 가장 많은 영화 제목은?");
  const [comments, setComments] = useState<CommentTable[]>([]);
  const [compareResult, setCompareResult] = useState<EnrichCompareResult | null>(null);

  // 데모 테이블 소유 스키마 — 인증 사용자 자신의 스키마 (없으면 ADMIN)
  // 공유 키 ["schema","owners"]의 반환 형태를 unwrap(SchemaOwnersResult)으로 통일 (ProfileEditor와 일치)
  const ownersQuery = useQuery({
    queryKey: ["schema", "owners"],
    queryFn: async () =>
      (await getEnvelope<SchemaOwnersResult>("/schema/owners", undefined, {
        suppressErrorToast: true,
      })).data,
    staleTime: 60_000,
  });
  const owner = ownersQuery.data?.current_schema ?? "ADMIN";

  // ① 모호 스키마 생성 (reset=true로 매번 깨끗한 "증강 전" 상태에서 시작)
  const createSchema = useMutation({
    mutationFn: () =>
      postEnvelope<DemoSchemaResult>("/enrichment/demo-schema", { reset: true }, {
        sqlLogTag: "PG-06/스키마생성",
      }),
    onSuccess: () => {
      pushToast({ status: "success", title: "모호 스키마(TABLE1~3) 생성 완료" });
      setStep(1);
    },
  });

  // ② comments off/on 프로파일 쌍 생성
  const createPair = useMutation({
    mutationFn: () => {
      const objectList: ObjectRef[] = DEMO_TABLES.map((name) => ({ owner, name }));
      return postEnvelope<ProfilePairResult>(
        "/enrichment/profile-pair",
        { base_name: "ENRICH_DEMO", object_list: objectList },
        { sqlLogTag: "PG-06/프로파일쌍" },
      );
    },
    onSuccess: () => {
      pushToast({ status: "success", title: `프로파일 쌍 생성 — ${PROFILE_OFF} / ${PROFILE_ON}` });
      void loadComments.mutate();
      setStep(2);
    },
  });

  // ③ 현재 COMMENT 로드 (편집용) — 데모 테이블(TABLE1~3)만 조회.
  // owner 전체(예: ADMIN 237개)를 부르면 매우 느리고(DPY-4024) 불필요하므로 테이블별로 가져온다.
  const loadComments = useMutation({
    mutationFn: async () => {
      const results = await Promise.all(
        DEMO_TABLES.map((t) =>
          getEnvelope<CommentsResult>("/enrichment/comments", { owner, table: t }, {
            suppressErrorToast: true,
          }),
        ),
      );
      return results.flatMap((r) => r.data.tables ?? []);
    },
    onSuccess: (tables) => setComments(tables),
  });

  // ③ COMMENT 적용 — 추천 문구(현재 입력값)를 컬럼별 COMMENT로 적용
  const applyComments = useMutation({
    mutationFn: async () => {
      // 편집된 컬럼 COMMENT만 모아 테이블별로 PUT (preview_only=false)
      for (const t of comments) {
        const columnComments: CommentEntry[] = t.columns
          .filter((c) => (c.comment ?? "").trim().length > 0)
          .map((c) => ({ table: t.table_name, column: c.column_name, comment: c.comment as string }));
        const tableComment: CommentEntry | null =
          (t.comment ?? "").trim().length > 0
            ? { table: t.table_name, comment: t.comment as string }
            : null;
        if (!columnComments.length && !tableComment) continue;
        await putEnvelope("/enrichment/comments", {
          owner,
          table_comment: tableComment,
          column_comments: columnComments,
          preview_only: false,
        }, { sqlLogTag: `PG-06/COMMENT:${t.table_name}` });
      }
    },
    onSuccess: () => {
      pushToast({ status: "success", title: "COMMENT 적용 완료 — 이제 'on' 프로파일이 의미를 압니다" });
      setStep(3);
    },
  });

  // ⑤ 전/후 비교 실행
  const runCompare = useMutation({
    mutationFn: () =>
      postEnvelope<EnrichCompareResult>(
        "/enrichment/compare",
        { prompt, profile_off: PROFILE_OFF, profile_on: PROFILE_ON, action: "showsql" },
        { sqlLogTag: "PG-06/비교" },
      ),
    onSuccess: (env) => {
      setCompareResult(env.data);
      setStep(4);
    },
  });

  // 데모 스키마 정리
  const cleanup = useMutation({
    mutationFn: () => deleteEnvelope("/enrichment/demo-schema", { sqlLogTag: "PG-06/정리" }),
    onSuccess: () => {
      pushToast({ status: "success", title: "데모 스키마·프로파일 쌍 정리 완료" });
      setStep(0);
      setComments([]);
      setCompareResult(null);
    },
  });

  const updateColumnComment = (ti: number, ci: number, value: string) => {
    setComments((prev) =>
      prev.map((t, i) =>
        i === ti
          ? { ...t, columns: t.columns.map((c, j) => (j === ci ? { ...c, comment: value } : c)) }
          : t,
      ),
    );
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Comment 증강 전/후 비교</h2>
          <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
            컬럼명이 모호한 스키마(c1~c7)는 LLM도 헷갈립니다. COMMENT로 의미를 주면 NL2SQL 정확도가
            달라지는 것을 좌우로 비교합니다 (가이드 p147–150).
          </p>
        </div>
        <Button variant="ghost" loading={cleanup.isPending} onClick={() => cleanup.mutate()}>
          데모 스키마 정리 ↺
        </Button>
      </div>

      {/* stepper */}
      <div className="flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <span
            key={label}
            className={`rounded-full px-3 py-1 text-sm ${
              i === step
                ? "bg-[var(--color-action-primary)] text-[var(--color-neutral-0)]"
                : i < step
                  ? "bg-[var(--color-success-tint)] text-[var(--color-success)]"
                  : "bg-[var(--color-neutral-20)] text-[var(--color-neutral-60)]"
            }`}
          >
            {label}
          </span>
        ))}
      </div>

      {/* ① 스키마 생성 */}
      <Panel title="① 모호 스키마 준비">
        <p className="mb-3 text-sm text-[var(--color-neutral-70)]">
          {owner} 스키마에 컬럼명이 c1~c7인 무비 테이블 3개(TABLE1~3)를 만듭니다. "사람도 못 알아보는
          스키마 — LLM도 마찬가지입니다."
        </p>
        <Button loading={createSchema.isPending} onClick={() => createSchema.mutate()}>
          데모 스키마 원클릭 생성
        </Button>
      </Panel>

      {/* ② 프로파일 쌍 */}
      <Panel title="② comments off/on 프로파일 쌍">
        <p className="mb-3 text-sm text-[var(--color-neutral-70)]">
          같은 대상 테이블에 <code>comments</code> 속성만 다른 두 프로파일({PROFILE_OFF} /{" "}
          {PROFILE_ON})을 한 번에 만듭니다.
        </p>
        <Button
          loading={createPair.isPending}
          disabled={step < 1}
          onClick={() => createPair.mutate()}
        >
          프로파일 쌍 생성
        </Button>
      </Panel>

      {/* ③ COMMENT 편집·적용 */}
      <Panel title="③ COMMENT 적용 (의미 부여)">
        {comments.length === 0 ? (
          <p className="text-sm text-[var(--color-neutral-60)]">
            프로파일 쌍 생성 후 컬럼 목록이 표시됩니다.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {comments.map((t, ti) => (
              <div key={t.table_name}>
                <p className="mb-1 font-mono text-sm font-semibold">{t.table_name}</p>
                <div className="flex flex-col gap-1">
                  {t.columns.map((c, ci) => (
                    <div key={c.column_name} className="flex items-center gap-2">
                      <span className="w-24 shrink-0 font-mono text-sm">{c.column_name}</span>
                      <span className="w-20 shrink-0 text-xs text-[var(--color-neutral-50)]">
                        {c.data_type}
                      </span>
                      <input
                        className="flex-1 rounded-[var(--radius-md)] border border-[var(--color-neutral-40)] px-2 py-1 text-sm"
                        placeholder="이 컬럼의 의미 (예: 영화 제목)"
                        value={c.comment ?? ""}
                        onChange={(e) => updateColumnComment(ti, ci, e.target.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <Button
              loading={applyComments.isPending}
              disabled={step < 2}
              onClick={() => applyComments.mutate()}
            >
              COMMENT 적용
            </Button>
          </div>
        )}
      </Panel>

      {/* ④ 비교 질문 + ⑤ 실행 */}
      <Panel title="④ 비교 질문 → ⑤ 전/후 실행">
        <textarea
          className="mb-3 w-full rounded-[var(--radius-md)] border border-[var(--color-neutral-40)] p-3 text-sm"
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <Button
          loading={runCompare.isPending}
          disabled={step < 3 || prompt.trim().length === 0}
          onClick={() => runCompare.mutate()}
        >
          전(off) / 후(on) 비교 실행
        </Button>
      </Panel>

      {/* 비교 결과 */}
      {compareResult ? (
        <ComparePanes
          beforeTitle={<>증강 전 — {PROFILE_OFF} (comments off)</>}
          afterTitle={<>증강 후 — {PROFILE_ON} (comments on)</>}
          before={<ComparePane side={compareResult.before} />}
          after={<ComparePane side={compareResult.after} />}
          summary={
            <>
              같은 질문 "{compareResult.prompt}" — COMMENT가 없을 때와 있을 때 LLM이 선택한 컬럼/테이블이
              어떻게 달라지는지 비교하세요. 증강 후가 의미를 정확히 짚어냅니다.
              {compareResult.augmented_prompt ? (
                <SqlBlock sql={compareResult.augmented_prompt} label="증강된 프롬프트(showprompt) 보기" />
              ) : null}
            </>
          }
        />
      ) : null}

      <Panel variant="explain">
        ⓘ 오답도 시연의 일부입니다. 증강 전 결과가 틀리거나 엉뚱한 컬럼을 고르는 것이 바로 COMMENT의
        가치를 보여주는 장면입니다. LLM이 우연히 맞히면 다른 질문으로 재시도하세요.
      </Panel>
    </div>
  );
}

export default Enrichment;
