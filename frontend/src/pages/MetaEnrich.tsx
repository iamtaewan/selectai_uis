/**
 * MetaEnrich 페이지 — 준비하기 ④ 메타 강화 (/meta) / FR-04 보강.
 * 프로파일 → 대상 테이블(object_list) → 테이블/컬럼 레벨 comment·annotation 관리.
 * COMMENT / ANNOTATION은 각각 별도 팝업으로 직접 편집.
 * "메타 제안 및 적용": 샘플 데이터 + 프로파일 내 다른 테이블 관계(FK)를 xai.grok-4로 분석해
 *   table/column 레벨 comment·annotation을 제안 → 검토(편집·선택) → 선택/전체 적용.
 * 근거: selectai-reference §3·§5, security §4(샘플 데이터 LLM 전송), Annotation 가이드 §4 표준 키.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { MessageSquareText, Tags } from "lucide-react";
import { Link } from "react-router-dom";

import { getEnvelope, postEnvelope, putEnvelope } from "../api/client";
import type { ProfileSummary } from "../api/types";
import Button from "../components/Button";
import Modal from "../components/Modal";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import { useToastStore } from "../components/Toast";
import { useConnectionStore } from "../store/connectionStore";

interface ProfileTable {
  owner: string;
  name: string;
}
interface AnnotationItem {
  name: string;
  value: string | null;
}
interface MetaColumn {
  column_name: string;
  data_type: string;
  nullable: boolean;
  comment: string | null;
  annotations: AnnotationItem[];
}
interface TableMetadata {
  owner: string;
  table_name: string;
  table_comment: string | null;
  table_annotations: AnnotationItem[];
  columns: MetaColumn[];
}
interface SuggestMeta {
  comment: string | null;
  annotations: AnnotationItem[];
}
interface SuggestColumn extends SuggestMeta {
  column: string;
}
interface SuggestResult {
  owner: string;
  table_name: string;
  model: string;
  sample_rows: number;
  table: SuggestMeta;
  columns: SuggestColumn[];
  raw: string;
}
interface ApplyItemResult {
  target: string;
  kind: string;
  ok: boolean;
  error?: string;
}
interface ApplyResult {
  results: ApplyItemResult[];
  summary: { done: number; failed: number };
}
interface PrivCheck {
  current_user: string;
  owner: string;
  owns_table: boolean;
  schema_protected: boolean;
  required: string[];
  held: string[];
  missing: string[];
  grantable: string[];
  can_grant_all: boolean;
  can_apply: boolean;
  grant_sql: string[];
  blocked_reason_ko: string | null;
}

/** 표준 어노테이션 키 딕셔너리 (Oracle Select AI Annotation 가이드 §4) */
interface KeyDef {
  key: string;
  label: string;
  level: "table" | "column";
  flag?: boolean;
  json?: boolean;
  example?: string;
  desc: string;
}
const ANNOTATION_KEYS: KeyDef[] = [
  { key: "business_name", label: "비즈니스 명칭", level: "column", example: "debt-to-income ratio", desc: "LLM/사용자용 비즈니스 명칭. 약어 컬럼엔 필수." },
  { key: "synonyms", label: "동의어", level: "column", example: "상태, 진행단계", desc: "사용자가 쓸 법한 동의어(콤마 구분)." },
  { key: "unit", label: "단위", level: "column", example: "percent", desc: "측정 단위 (percent/KRW/days 등)." },
  { key: "range", label: "유효 범위", level: "column", example: "0~100", desc: "유효 값의 범위." },
  { key: "value_map", label: "코드-라벨 매핑", level: "column", json: true, example: '{"A":"승인","R":"심사중"}', desc: "코드성 컬럼의 코드→라벨 매핑(JSON)." },
  { key: "note", label: "계산식·주의", level: "column", example: "월부채 / 월소득", desc: "계산식이나 주의사항." },
  { key: "join_hint", label: "조인 가이드", level: "column", example: "customers.cust_no 와 조인", desc: "조인 방법 힌트." },
  { key: "pk", label: "PK 표시", level: "column", flag: true, desc: "기본키 표시 (플래그, 값 없음)." },
  { key: "fk", label: "FK 표시", level: "column", flag: true, desc: "외래키 표시 (플래그, 값 없음)." },
  { key: "pii", label: "개인정보", level: "column", example: "true", desc: "개인정보 여부 (true/false)." },
  { key: "classification", label: "데이터 분류", level: "column", example: "RRN", desc: "데이터 분류 (RRN/PUBLIC 등)." },
  { key: "column_hidden", label: "프롬프트 노출 제외", level: "column", flag: true, desc: "프롬프트 노출 제외 의도 (플래그). 확실한 차단은 뷰/스코핑 병행." },
  { key: "domain", label: "업무 도메인", level: "table", example: "credit", desc: "업무 도메인 (credit/billing 등)." },
  { key: "source_system", label: "원천 시스템", level: "table", example: "여신코어", desc: "데이터 원천 시스템." },
  { key: "refresh", label: "갱신 주기", level: "table", example: "daily", desc: "데이터 갱신 주기." },
  { key: "owner", label: "데이터 오너", level: "table", example: "CSE Data Team", desc: "데이터 소유 주체." },
];
const QUICK_KEYS_COLUMN = ["business_name", "value_map", "unit", "join_hint", "pii"];
const QUICK_KEYS_TABLE = ["domain", "source_system", "owner"];

// 제안 검토용 편집 모델 (value는 string, 빈 문자열 = 값 없음)
interface AnnDraft {
  name: string;
  value: string;
}
interface MetaDraft {
  selected: boolean;
  comment: string;
  annotations: AnnDraft[];
}
interface Proposal {
  model: string;
  sampleRows: number;
  raw: string;
  table: MetaDraft;
  columns: Record<string, MetaDraft>;
  columnOrder: string[];
}

type EditKind = "comment" | "annotation";
type EditTarget =
  | { kind: EditKind; level: "table" }
  | { kind: EditKind; level: "column"; column: string };

const toDraft = (m: SuggestMeta): MetaDraft => ({
  selected: true,
  comment: m.comment ?? "",
  annotations: (m.annotations ?? []).map((a) => ({ name: a.name, value: a.value ?? "" })),
});

export function MetaEnrich() {
  const activeConnection = useConnectionStore((s) => s.activeConnection);
  const pushToast = useToastStore((s) => s.push);

  const [profile, setProfile] = useState("");
  const [selected, setSelected] = useState<ProfileTable | null>(null);
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);

  // 직접 편집 팝업 입력
  const [commentDraft, setCommentDraft] = useState("");
  const [annName, setAnnName] = useState("");
  const [annValue, setAnnValue] = useState("");
  const [editingAnn, setEditingAnn] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  // 제안 검토
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [applyResults, setApplyResults] = useState<ApplyItemResult[] | null>(null);

  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await getEnvelope<ProfileSummary[]>("/profiles")).data,
  });
  const profiles = profilesQuery.data ?? [];

  const tablesQuery = useQuery({
    queryKey: ["meta", "profile-tables", profile],
    queryFn: async () =>
      (await getEnvelope<{ tables: ProfileTable[] }>("/meta/profile-tables", { profile }, {
        suppressErrorToast: true,
      })).data.tables,
    enabled: !!profile,
  });
  const tables = tablesQuery.data ?? [];

  const metaQuery = useQuery({
    queryKey: ["meta", "table", selected?.owner, selected?.name],
    queryFn: async () =>
      (await getEnvelope<TableMetadata>("/meta/table-metadata", {
        owner: selected!.owner,
        table: selected!.name,
      })).data,
    enabled: !!selected,
  });
  const metadata = metaQuery.data;

  // 권한 점검 — 대상 테이블 선택 시
  const privQuery = useQuery({
    queryKey: ["meta", "priv", selected?.owner, selected?.name],
    queryFn: async () =>
      (await getEnvelope<PrivCheck>("/meta/privilege-check", {
        owner: selected!.owner,
        table: selected!.name,
      }, { suppressErrorToast: true })).data,
    enabled: !!selected,
  });
  const priv = privQuery.data;
  const canApply = priv?.can_apply ?? true; // 점검 전엔 허용(점검 후 게이트)

  const target = useMemo(() => {
    if (!editTarget || !metadata) return null;
    if (editTarget.level === "table") {
      return {
        label: `${metadata.owner}.${metadata.table_name} (테이블)`,
        comment: metadata.table_comment,
        annotations: metadata.table_annotations,
        column: null as string | null,
      };
    }
    const col = metadata.columns.find((c) => c.column_name === editTarget.column);
    return {
      label: `${metadata.table_name}.${editTarget.column} (컬럼)`,
      comment: col?.comment ?? null,
      annotations: col?.annotations ?? [],
      column: editTarget.column,
    };
  }, [editTarget, metadata]);

  const tag = (a: string) => `PG-meta/${a}`;

  const applyComment = useMutation({
    mutationFn: () =>
      putEnvelope("/meta/comments", {
        owner: selected!.owner,
        table: selected!.name,
        column: target?.column ?? null,
        comment: commentDraft,
      }, { sqlLogTag: tag("comment") }),
    onSuccess: () => {
      pushToast({ status: "success", title: "COMMENT 적용" });
      void metaQuery.refetch();
      setEditTarget(null);
    },
  });

  const annotationMut = useMutation({
    mutationFn: (vars: { name: string; value: string | null; operation: "add" | "replace" | "drop" }) =>
      putEnvelope("/meta/annotations", {
        owner: selected!.owner,
        table: selected!.name,
        column: target?.column ?? null,
        ...vars,
      }, { sqlLogTag: tag(`annotation:${vars.operation}`) }),
    onSuccess: (_d, vars) => {
      pushToast({ status: "success", title: `ANNOTATION ${vars.operation.toUpperCase()} 적용` });
      setAnnName("");
      setAnnValue("");
      setEditingAnn(null);
      void metaQuery.refetch();
    },
  });

  // 메타 제안 (grok-4)
  const suggest = useMutation({
    mutationFn: () =>
      postEnvelope<SuggestResult>("/meta/suggest", {
        owner: selected!.owner,
        table: selected!.name,
        profile: profile || null,
      }, { sqlLogTag: tag("grok-제안") }),
    onSuccess: (env) => {
      const r = env.data;
      setProposal({
        model: r.model,
        sampleRows: r.sample_rows,
        raw: r.raw,
        table: toDraft(r.table),
        columns: Object.fromEntries(r.columns.map((c) => [c.column, toDraft(c)])),
        columnOrder: r.columns.map((c) => c.column),
      });
      setReviewOpen(true);
    },
  });

  // 선택/일괄 적용
  const applyBatch = useMutation({
    mutationFn: (onlySelected: boolean) => {
      const items: unknown[] = [];
      const pack = (m: MetaDraft) => ({
        comment: m.comment.trim() || null,
        annotations: m.annotations
          .filter((a) => a.name.trim())
          .map((a) => ({ name: a.name.trim(), value: a.value.trim() || null })),
      });
      if (proposal && (!onlySelected || proposal.table.selected)) {
        items.push({ level: "table", ...pack(proposal.table) });
      }
      for (const col of proposal?.columnOrder ?? []) {
        const m = proposal!.columns[col];
        if (onlySelected && !m.selected) continue;
        items.push({ level: "column", column: col, ...pack(m) });
      }
      return postEnvelope<ApplyResult>("/meta/apply", {
        owner: selected!.owner,
        table: selected!.name,
        items,
      }, { sqlLogTag: tag("일괄적용") });
    },
    onSuccess: (env) => {
      const s = env.data.summary;
      setApplyResults(env.data.results);
      // 권한 오류 감지 → 안내
      const firstErr = env.data.results.find((r) => !r.ok)?.error;
      const privIssue = env.data.results.some(
        (r) => r.error && (r.error.includes("권한") || r.error.includes("01031") || r.error.includes("41900")),
      );
      pushToast({
        status: s.failed > 0 ? (s.done > 0 ? "warning" : "error") : "success",
        title: `메타 적용 — 성공 ${s.done}, 실패 ${s.failed}`,
        body:
          s.failed > 0
            ? privIssue
              ? "권한 부족: 접속 사용자가 소유하지 않은 스키마(예: SH)는 수정할 수 없습니다."
              : (firstErr ?? "일부 항목 적용 실패")
            : undefined,
      });
      if (s.failed === 0) setReviewOpen(false);
      void metaQuery.refetch();
    },
  });

  // 권한 부여 (부여 가능한 권한만)
  const grantMut = useMutation({
    mutationFn: () =>
      postEnvelope<{ summary: { done: number; failed: number }; results: { privilege: string; ok: boolean; error?: string }[] }>(
        "/meta/grant",
        { privileges: priv?.grantable ?? [] },
        { sqlLogTag: tag("권한부여") },
      ),
    onSuccess: (env) => {
      const s = env.data.summary;
      const err = env.data.results.find((r) => !r.ok)?.error;
      pushToast({
        status: s.failed > 0 ? "warning" : "success",
        title: `권한 부여 — 성공 ${s.done}, 실패 ${s.failed}`,
        body: s.failed > 0 ? err : undefined,
      });
      void privQuery.refetch();
    },
  });

  // ── proposal 편집 헬퍼 ──
  const updTable = (fn: (m: MetaDraft) => MetaDraft) =>
    setProposal((p) => (p ? { ...p, table: fn(p.table) } : p));
  const updCol = (col: string, fn: (m: MetaDraft) => MetaDraft) =>
    setProposal((p) => (p ? { ...p, columns: { ...p.columns, [col]: fn(p.columns[col]) } } : p));
  const selectedCount = useMemo(() => {
    if (!proposal) return 0;
    return (proposal.table.selected ? 1 : 0) + proposal.columnOrder.filter((c) => proposal.columns[c].selected).length;
  }, [proposal]);

  const openComment = (t: EditTarget) => {
    setEditTarget(t);
    const cur =
      t.level === "table"
        ? metadata?.table_comment
        : metadata?.columns.find((c) => c.column_name === t.column)?.comment;
    setCommentDraft(cur ?? "");
  };
  const openAnnotation = (t: EditTarget) => {
    setEditTarget(t);
    setAnnName("");
    setAnnValue("");
    setEditingAnn(null);
  };
  const closeModal = () => setEditTarget(null);

  // 직접 편집 팝업의 제안 채우기 (proposal에서 도출)
  const currentSuggestion = useMemo(() => {
    if (!proposal || editTarget?.level !== "column") return undefined;
    const m = proposal.columns[editTarget.column];
    if (!m) return undefined;
    return { comment: m.comment, annotation: m.annotations[0]?.name ?? "" };
  }, [proposal, editTarget]);

  const annLevel: "table" | "column" = editTarget?.level === "table" ? "table" : "column";
  const levelKeys = ANNOTATION_KEYS.filter((k) => k.level === annLevel);
  const quickKeys = annLevel === "table" ? QUICK_KEYS_TABLE : QUICK_KEYS_COLUMN;
  const activeKeyDef = ANNOTATION_KEYS.find((k) => k.key === annName.trim().toLowerCase());
  const pickKey = (key: string) => {
    setAnnName(key);
    if (ANNOTATION_KEYS.find((k) => k.key === key)?.flag) setAnnValue("");
  };

  const RowActions = ({ level, column }: { level: "table" | "column"; column?: string }) => {
    const t = (level === "table" ? { level } : { level, column: column! }) as Omit<EditTarget, "kind">;
    return (
      <div className="flex justify-end gap-1">
        <Button
          variant="ghost"
          className="!px-2 text-sm whitespace-nowrap"
          onClick={() => openComment({ ...t, kind: "comment" } as EditTarget)}
        >
          <MessageSquareText size={14} aria-hidden />
          코멘트
        </Button>
        <Button
          variant="ghost"
          className="!px-2 text-sm whitespace-nowrap"
          onClick={() => openAnnotation({ ...t, kind: "annotation" } as EditTarget)}
        >
          <Tags size={14} aria-hidden />
          어노테이션
        </Button>
      </div>
    );
  };

  if (!activeConnection) {
    return (
      <Panel title="메타 강화">
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
        <h2 className="text-2xl font-bold">메타 강화</h2>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          대상 테이블에 comment·annotation을 부여해 NL2SQL 정확도를 높입니다. 행의 [코멘트]·[어노테이션]
          으로 직접 편집하거나, [메타 제안 및 적용]으로 grok-4 분석 결과를 검토·일괄 적용할 수 있습니다.
        </p>
      </div>

      {/* ① 프로파일 → 테이블 선택 */}
      <Panel title="① 프로파일 · 대상 테이블 선택">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            프로파일
            <select
              className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2"
              value={profile}
              onChange={(e) => {
                setProfile(e.target.value);
                setSelected(null);
                setProposal(null);
              }}
            >
              <option value="">선택…</option>
              {profiles.map((p) => (
                <option key={p.profile_name} value={p.profile_name}>
                  {p.profile_name}
                </option>
              ))}
            </select>
          </label>
          {profile && tablesQuery.isFetching ? (
            <span className="text-sm text-[var(--color-neutral-60)]">대상 테이블 조회 중…</span>
          ) : null}
        </div>

        {profile && tables.length === 0 && !tablesQuery.isFetching ? (
          <p className="mt-3 text-sm text-[var(--color-neutral-60)]">
            이 프로파일에는 object_list 대상 테이블이 지정되어 있지 않습니다. 프로파일 편집에서 대상
            테이블을 지정하면 여기서 선택할 수 있습니다.
          </p>
        ) : null}

        {tables.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {tables.map((t) => {
              const isSel = selected?.owner === t.owner && selected?.name === t.name;
              return (
                <button
                  key={`${t.owner}.${t.name}`}
                  className={`rounded-full border px-3 py-1 font-mono text-sm ${
                    isSel
                      ? "border-[var(--color-brand)] bg-[var(--color-info-tint)] font-bold"
                      : "border-[var(--color-neutral-40)] hover:bg-[var(--color-neutral-20)]"
                  }`}
                  onClick={() => {
                    setSelected(t);
                    setProposal(null);
                  }}
                >
                  {t.owner}.{t.name}
                </button>
              );
            })}
          </div>
        ) : null}
      </Panel>

      {/* ② 메타데이터 표 */}
      {selected ? (
        <Panel
          title={
            <span className="flex items-center justify-between gap-3">
              <span>
                ② {selected.owner}.{selected.name} — 메타데이터
              </span>
              <span className="flex gap-2">
                {proposal ? (
                  <Button variant="ghost" onClick={() => setReviewOpen(true)}>
                    제안 검토 다시 열기
                  </Button>
                ) : null}
                <Button variant="secondary" loading={suggest.isPending} onClick={() => suggest.mutate()}>
                  ✦ 메타 제안 및 적용
                </Button>
              </span>
            </span>
          }
        >
          {/* 권한 점검 배너 */}
          {privQuery.isFetching && !priv ? (
            <p className="mb-3 text-sm text-[var(--color-running)]">권한 점검 중…</p>
          ) : priv ? (
            priv.can_apply ? (
              <div className="mb-3 flex items-center gap-2">
                <StatusBadge status="success">메타 적용 가능</StatusBadge>
                <span className="text-xs text-[var(--color-neutral-60)]">
                  {priv.owns_table
                    ? `${priv.current_user}이(가) 소유한 테이블`
                    : `권한 보유 (${priv.held.join(", ")})`}
                </span>
              </div>
            ) : (
              <div className="mb-3 rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-danger-tint)] p-3">
                <div className="flex items-center gap-2">
                  <StatusBadge status="error">적용 불가</StatusBadge>
                  {priv.schema_protected ? (
                    <span className="text-sm font-medium">보호 스키마 (oracle_maintained)</span>
                  ) : (
                    <span className="text-sm font-medium">권한 부족</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-[var(--color-neutral-70)]">{priv.blocked_reason_ko}</p>
                {/* 부여 가능한 권한이 있으면 부여 버튼 */}
                {priv.missing.length > 0 && priv.can_grant_all ? (
                  <div className="mt-2">
                    <p className="text-xs text-[var(--color-neutral-60)]">
                      실행될 GRANT: {priv.grant_sql.join("; ")}
                    </p>
                    <Button
                      variant="secondary"
                      loading={grantMut.isPending}
                      onClick={() => grantMut.mutate()}
                    >
                      권한 부여
                    </Button>
                  </div>
                ) : null}
              </div>
            )
          ) : null}

          {metaQuery.isPending ? (
            <p className="text-sm text-[var(--color-running)]">메타데이터 조회 중…</p>
          ) : metadata ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-neutral-40)] text-left">
                    <th className="px-2 py-2">대상</th>
                    <th className="px-2 py-2">타입</th>
                    <th className="px-2 py-2">COMMENT</th>
                    <th className="px-2 py-2">ANNOTATION</th>
                    <th className="px-2 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[var(--color-neutral-30)] bg-[var(--color-neutral-10)] align-top">
                    <td className="px-2 py-2 font-mono font-bold">📋 {metadata.table_name}</td>
                    <td className="px-2 py-2 text-[var(--color-neutral-60)]">테이블</td>
                    <td className="px-2 py-2">{metadata.table_comment ?? "—"}</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-1">
                        {metadata.table_annotations.map((a) => (
                          <StatusBadge key={a.name} status="neutral">
                            {a.name}
                            {a.value ? `=${a.value}` : ""}
                          </StatusBadge>
                        ))}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-right">
                      <RowActions level="table" />
                    </td>
                  </tr>
                  {metadata.columns.map((col) => {
                    const hasSug = !!proposal?.columns[col.column_name];
                    return (
                      <tr
                        key={col.column_name}
                        className="border-b border-[var(--color-neutral-20)] align-top"
                      >
                        <td className="px-2 py-2 font-mono font-semibold">
                          {col.column_name}
                          {hasSug ? <span className="ml-1 text-[var(--color-brand)]">✦</span> : null}
                        </td>
                        <td className="px-2 py-2 text-[var(--color-neutral-60)]">{col.data_type}</td>
                        <td className="px-2 py-2">{col.comment ?? "—"}</td>
                        <td className="px-2 py-2">
                          <div className="flex flex-wrap gap-1">
                            {col.annotations.map((a) => (
                              <StatusBadge key={a.name} status="neutral">
                                {a.name}
                                {a.value ? `=${a.value}` : ""}
                              </StatusBadge>
                            ))}
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 text-right">
                          <RowActions level="column" column={col.column_name} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </Panel>
      ) : null}

      {/* 제안 검토 & 적용 모달 */}
      <Modal
        open={reviewOpen && !!proposal}
        title={`메타 제안 검토 — ${selected?.owner}.${selected?.name}`}
        onClose={() => setReviewOpen(false)}
        maxWidth="56rem"
        footer={
          <>
            <span className="mr-auto self-center text-xs text-[var(--color-neutral-60)]">
              {proposal ? `${proposal.model} · 샘플 ${proposal.sampleRows}행 분석 · 선택 ${selectedCount}건` : ""}
            </span>
            <Button variant="secondary" onClick={() => setReviewOpen(false)}>
              닫기
            </Button>
            <Button
              variant="secondary"
              loading={applyBatch.isPending && applyBatch.variables === true}
              disabled={selectedCount === 0 || !canApply}
              title={!canApply ? "권한/보호 스키마 제약으로 적용할 수 없습니다" : undefined}
              onClick={() => applyBatch.mutate(true)}
            >
              선택 적용 ({selectedCount})
            </Button>
            <Button
              loading={applyBatch.isPending && applyBatch.variables === false}
              disabled={!canApply}
              title={!canApply ? "권한/보호 스키마 제약으로 적용할 수 없습니다" : undefined}
              onClick={() => applyBatch.mutate(false)}
            >
              전체 적용
            </Button>
          </>
        }
      >
        {proposal ? (
          <div className="flex flex-col gap-3">
            <Panel variant="explain">
              ✦ grok-4가 샘플 데이터와 프로파일 내 다른 테이블/FK 관계를 분석한 제안입니다. 각 항목을
              편집·선택한 뒤 적용하세요. 적용은 DB에 DDL로 즉시 반영됩니다.
            </Panel>

            {/* 적용 결과 — 실패 항목 사유 표시 */}
            {applyResults && applyResults.some((r) => !r.ok) ? (
              <div className="rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-danger-tint)] p-3">
                <p className="mb-1 text-sm font-semibold text-[var(--color-danger)]">
                  적용 실패 {applyResults.filter((r) => !r.ok).length}건
                </p>
                <ul className="flex max-h-40 flex-col gap-0.5 overflow-auto text-xs">
                  {applyResults
                    .filter((r) => !r.ok)
                    .slice(0, 30)
                    .map((r, i) => (
                      <li key={i}>
                        <span className="font-mono">{r.target} · {r.kind}</span> — {r.error}
                      </li>
                    ))}
                </ul>
                <p className="mt-2 text-xs text-[var(--color-neutral-70)]">
                  ⓘ 대부분 <b>권한 부족</b>입니다. 접속 사용자(예: ADMIN)가 <b>소유하지 않은 스키마</b>(예:
                  SH 샘플)의 테이블은 COMMENT/ALTER 할 수 없습니다. 본인 스키마(ADMIN 소유) 테이블을
                  대상으로 하거나, 해당 객체에 대한 권한을 확보하세요.
                </p>
              </div>
            ) : null}

            {/* 테이블 레벨 */}
            <DraftCard
              title={`📋 ${selected?.name} (테이블)`}
              draft={proposal.table}
              level="table"
              onChange={updTable}
            />
            {/* 컬럼 레벨 */}
            {proposal.columnOrder.map((col) => (
              <DraftCard
                key={col}
                title={`${col} (컬럼)`}
                draft={proposal.columns[col]}
                level="column"
                onChange={(fn) => updCol(col, fn)}
              />
            ))}

            <details>
              <summary className="cursor-pointer text-xs text-[var(--color-link)]">
                grok-4 응답 원문 보기
              </summary>
              <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-[var(--radius-sm)] bg-[var(--color-neutral-10)] p-2 font-mono text-xs">
                {proposal.raw}
              </pre>
            </details>
          </div>
        ) : null}
      </Modal>

      {/* COMMENT 직접 편집 팝업 */}
      <Modal
        open={editTarget?.kind === "comment" && !!target}
        title={`COMMENT 편집 — ${target?.label ?? ""}`}
        onClose={closeModal}
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>
              취소
            </Button>
            <Button
              loading={applyComment.isPending}
              disabled={!canApply}
              title={!canApply ? "권한/보호 스키마 제약으로 적용할 수 없습니다" : undefined}
              onClick={() => applyComment.mutate()}
            >
              COMMENT 저장
            </Button>
          </>
        }
      >
        {target ? (
          <div className="flex flex-col gap-2">
            {currentSuggestion?.comment ? (
              <div className="flex items-center justify-between rounded-[var(--radius-sm)] bg-[var(--color-info-tint)] p-2 text-xs">
                <span>✦ grok 제안: {currentSuggestion.comment}</span>
                <button
                  className="text-[var(--color-link)] underline"
                  onClick={() => setCommentDraft(currentSuggestion.comment)}
                >
                  채우기
                </button>
              </div>
            ) : null}
            <textarea
              className="w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] p-2 text-sm"
              rows={3}
              placeholder="이 대상의 의미 (예: 고객이 거주하는 도시)"
              value={commentDraft}
              onChange={(e) => setCommentDraft(e.target.value)}
            />
          </div>
        ) : null}
      </Modal>

      {/* ANNOTATION 직접 편집 팝업 */}
      <Modal
        open={editTarget?.kind === "annotation" && !!target}
        title={`ANNOTATION 편집 — ${target?.label ?? ""}`}
        onClose={closeModal}
        footer={
          <Button variant="secondary" onClick={closeModal}>
            닫기
          </Button>
        }
      >
        {target ? (
          <div className="flex flex-col gap-4">
            {target.annotations.length === 0 ? (
              <p className="text-sm text-[var(--color-neutral-60)]">등록된 어노테이션이 없습니다.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {target.annotations.map((a) => (
                  <li
                    key={a.name}
                    className="flex items-center gap-2 border-b border-[var(--color-neutral-20)] py-1"
                  >
                    <span className="font-mono text-sm font-semibold">{a.name}</span>
                    {editingAnn === a.name ? (
                      <>
                        <input
                          className="h-8 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 text-sm"
                          value={editingValue}
                          onChange={(e) => setEditingValue(e.target.value)}
                          placeholder="새 값"
                        />
                        <Button
                          loading={annotationMut.isPending}
                          onClick={() =>
                            annotationMut.mutate({
                              name: a.name,
                              value: editingValue || null,
                              operation: "replace",
                            })
                          }
                        >
                          저장
                        </Button>
                        <Button variant="ghost" onClick={() => setEditingAnn(null)}>
                          취소
                        </Button>
                      </>
                    ) : (
                      <>
                        <span className="flex-1 text-sm text-[var(--color-neutral-70)]">
                          {a.value ?? "(값 없음)"}
                        </span>
                        <Button
                          variant="ghost"
                          onClick={() => {
                            setEditingAnn(a.name);
                            setEditingValue(a.value ?? "");
                          }}
                        >
                          편집
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => {
                            if (window.confirm(`어노테이션 ${a.name}을(를) 삭제할까요?`))
                              annotationMut.mutate({ name: a.name, value: null, operation: "drop" });
                          }}
                        >
                          삭제
                        </Button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {/* 새 어노테이션 추가 — 표준 키 딕셔너리 기반 */}
            <div className="rounded-[var(--radius-md)] border border-[var(--color-neutral-30)] p-3">
              <h4 className="mb-2 text-sm font-semibold">새 어노테이션 추가</h4>
              <div className="mb-2 flex flex-wrap items-center gap-1">
                <span className="text-xs text-[var(--color-neutral-60)]">자주 쓰는 키:</span>
                {quickKeys.map((k) => (
                  <button
                    key={k}
                    className="rounded-full border border-[var(--color-neutral-40)] px-2 py-0.5 font-mono text-xs hover:bg-[var(--color-neutral-20)]"
                    onClick={() => pickKey(k)}
                  >
                    {k}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-end gap-2">
                <div className="flex flex-col">
                  <label className="text-xs text-[var(--color-neutral-60)]">표준 키</label>
                  <select
                    className="h-8 w-44 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 text-sm"
                    value={activeKeyDef?.key ?? ""}
                    onChange={(e) => (e.target.value ? pickKey(e.target.value) : setAnnName(""))}
                  >
                    <option value="">직접 입력…</option>
                    {levelKeys.map((k) => (
                      <option key={k.key} value={k.key}>
                        {k.key} — {k.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-[var(--color-neutral-60)]">이름</label>
                  <input
                    className="h-8 w-36 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 font-mono text-sm"
                    placeholder="business_name"
                    value={annName}
                    onChange={(e) => setAnnName(e.target.value)}
                  />
                </div>
                {activeKeyDef?.flag ? (
                  <div className="flex flex-col">
                    <label className="text-xs text-[var(--color-neutral-60)]">값</label>
                    <span className="flex h-8 items-center rounded-[var(--radius-sm)] bg-[var(--color-neutral-20)] px-3 text-xs text-[var(--color-neutral-60)]">
                      플래그 (값 없음)
                    </span>
                  </div>
                ) : activeKeyDef?.json ? (
                  <div className="flex flex-1 flex-col">
                    <label className="text-xs text-[var(--color-neutral-60)]">값 (JSON)</label>
                    <textarea
                      className="min-w-64 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] p-2 font-mono text-xs"
                      rows={2}
                      placeholder={activeKeyDef.example}
                      value={annValue}
                      onChange={(e) => setAnnValue(e.target.value)}
                    />
                  </div>
                ) : (
                  <div className="flex flex-col">
                    <label className="text-xs text-[var(--color-neutral-60)]">값 (선택)</label>
                    <input
                      className="h-8 w-44 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 text-sm"
                      placeholder={activeKeyDef?.example ?? "값"}
                      value={annValue}
                      onChange={(e) => setAnnValue(e.target.value)}
                    />
                  </div>
                )}
                <Button
                  disabled={!annName.trim() || !canApply}
                  title={!canApply ? "권한/보호 스키마 제약으로 적용할 수 없습니다" : undefined}
                  loading={annotationMut.isPending && annotationMut.variables?.operation === "add"}
                  onClick={() =>
                    annotationMut.mutate({
                      name: annName,
                      value: activeKeyDef?.flag ? null : annValue || null,
                      operation: "add",
                    })
                  }
                >
                  추가
                </Button>
              </div>
              {activeKeyDef ? (
                <p className="mt-2 text-xs text-[var(--color-neutral-60)]">ⓘ {activeKeyDef.desc}</p>
              ) : null}
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

/** 제안 검토 카드 — 선택 + comment 편집 + annotations 편집(값 수정/삭제/추가) */
function DraftCard({
  title,
  draft,
  level,
  onChange,
}: {
  title: string;
  draft: MetaDraft;
  level: "table" | "column";
  onChange: (fn: (m: MetaDraft) => MetaDraft) => void;
}) {
  const keys = ANNOTATION_KEYS.filter((k) => k.level === level);
  const setAnn = (idx: number, patch: Partial<AnnDraft>) =>
    onChange((m) => ({
      ...m,
      annotations: m.annotations.map((a, i) => (i === idx ? { ...a, ...patch } : a)),
    }));
  const removeAnn = (idx: number) =>
    onChange((m) => ({ ...m, annotations: m.annotations.filter((_, i) => i !== idx) }));
  const addAnn = () => onChange((m) => ({ ...m, annotations: [...m.annotations, { name: "", value: "" }] }));

  return (
    <div
      className={`rounded-[var(--radius-md)] border p-3 ${
        draft.selected ? "border-[var(--color-brand)]" : "border-[var(--color-neutral-30)] opacity-70"
      }`}
    >
      <label className="mb-2 flex items-center gap-2">
        <input
          type="checkbox"
          checked={draft.selected}
          onChange={(e) => onChange((m) => ({ ...m, selected: e.target.checked }))}
        />
        <span className="font-mono text-sm font-semibold">{title}</span>
      </label>

      <div className="mb-2">
        <label className="text-xs text-[var(--color-neutral-60)]">COMMENT</label>
        <input
          className="h-8 w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 text-sm"
          value={draft.comment}
          placeholder="(제안 없음 — 비우면 적용 안 함)"
          onChange={(e) => onChange((m) => ({ ...m, comment: e.target.value }))}
        />
      </div>

      <label className="text-xs text-[var(--color-neutral-60)]">ANNOTATIONS</label>
      <div className="flex flex-col gap-1">
        {draft.annotations.map((a, i) => (
          <div key={i} className="flex items-center gap-1">
            <input
              list={`keys-${level}`}
              className="h-8 w-36 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 font-mono text-xs"
              value={a.name}
              placeholder="키"
              onChange={(e) => setAnn(i, { name: e.target.value })}
            />
            <input
              className="h-8 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] px-2 text-xs"
              value={a.value}
              placeholder="값(선택)"
              onChange={(e) => setAnn(i, { value: e.target.value })}
            />
            <button
              className="px-2 text-[var(--color-danger)]"
              aria-label="삭제"
              onClick={() => removeAnn(i)}
            >
              ×
            </button>
          </div>
        ))}
        <datalist id={`keys-${level}`}>
          {keys.map((k) => (
            <option key={k.key} value={k.key}>
              {k.label}
            </option>
          ))}
        </datalist>
        <button
          className="self-start text-xs text-[var(--color-link)] underline"
          onClick={addAnn}
        >
          + 어노테이션 추가
        </button>
      </div>
    </div>
  );
}

export default MetaEnrich;
