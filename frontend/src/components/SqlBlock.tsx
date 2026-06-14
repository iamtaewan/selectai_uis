/**
 * SqlBlock — style.md §5.6 다크 코드 패널 (--color-code-* 토큰).
 * 기본은 <details> 접힘. 미리보기 모드는 "미리보기 — 아직 실행되지 않음" warning 배지.
 * highlightSql()은 SqlLogTerminal(§5.9)과 공유하는 간단 SQL 구문 강조 — 동일 토큰 사용.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Check, Copy } from "lucide-react";

import StatusBadge from "./StatusBadge";

// 강조 대상(§5.6): SQL 키워드 / DBMS_CLOUD_AI.* 함수명 / 문자열(프롬프트·JSON) / 주석
const TOKEN_RE =
  /('(?:[^']|'')*')|(--[^\n]*)|(\b(?:DBMS|UTL|SYS)_\w+(?:\.\w+)*\b)|(\b(?:SELECT|FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|BEGIN|END|DECLARE|EXCEPTION|CREATE|OR\s+REPLACE|DROP|ALTER|TABLE|VIEW|INDEX|INSERT|INTO|VALUES|UPDATE|SET|DELETE|MERGE|GRANT|REVOKE|COMMENT|COLUMN|ON|IS|AS|AND|OR|NOT|NULL|IN|LIKE|BETWEEN|JOIN|LEFT|RIGHT|INNER|OUTER|UNION|ALL|DISTINCT|COUNT|SUM|AVG|MIN|MAX|EXECUTE|IMMEDIATE|PROCEDURE|FUNCTION|RETURN|DUAL|TO)\b)/gi;

/** SQL 텍스트 → --color-code-* 토큰 기반 강조 노드 (SqlBlock·SqlLogTerminal 공용) */
export function highlightSql(sql: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  TOKEN_RE.lastIndex = 0;
  for (let m = TOKEN_RE.exec(sql); m !== null; m = TOKEN_RE.exec(sql)) {
    if (m.index > lastIndex) nodes.push(sql.slice(lastIndex, m.index));
    const [text] = m;
    const color = m[1]
      ? "var(--color-code-string)"
      : m[2]
        ? "var(--color-code-comment)"
        : m[3]
          ? "var(--color-code-accent)"
          : "var(--color-code-keyword)";
    nodes.push(
      <span key={key++} style={{ color }}>
        {text}
      </span>,
    );
    lastIndex = m.index + text.length;
  }
  if (lastIndex < sql.length) nodes.push(sql.slice(lastIndex));
  return nodes;
}

// 줄바꿈을 넣을 주요 절 키워드 (괄호 밖 가독성용)
const CLAUSE_RE =
  /\s+\b(FROM|WHERE|GROUP BY|ORDER BY|HAVING|INNER JOIN|LEFT JOIN|RIGHT JOIN|FULL JOIN|CROSS JOIN|JOIN|UNION ALL|UNION|ON)\b/gi;

/**
 * 한 줄로 정규화된 SQL을 가독성 좋게 복수 라인으로 포맷.
 * ① 문자열 리터럴을 보호(내부의 콤마/키워드 오인 방지) → ② DBMS_CLOUD_AI.*( ... ) 인자 줄바꿈
 * → ③ 주요 절 키워드 앞 줄바꿈 → ④ 문자열 복원.
 */
export function formatSql(raw: string): string {
  if (!raw || !raw.trim()) return raw;
  // ① 문자열 리터럴 보호 ('' escape 포함)
  const strs: string[] = [];
  let s = raw.replace(/'(?:[^']|'')*'/g, (m) => {
    strs.push(m);
    return `\x00${strs.length - 1}\x00`;
  });
  s = s.replace(/\s+/g, " ").trim();

  // ② DBMS_CLOUD_AI 함수 호출: 인자(name => value)를 한 줄씩 (문자열 보호로 괄호/콤마 없음)
  s = s.replace(
    /\b(DBMS_CLOUD_AI\.\w+)\s*\(([^()]*)\)/gi,
    (full, fn: string, args: string) => {
      if (!args.includes("=>")) return full;
      const body = args
        .split(",")
        .map((p) => "    " + p.trim())
        .join(",\n");
      return `${fn}(\n${body}\n)`;
    },
  );

  // ③ 주요 절 키워드 앞 줄바꿈
  s = s.replace(CLAUSE_RE, "\n$1");

  // ④ 문자열 복원
  s = s.replace(/\x00(\d+)\x00/g, (_m, i) => strs[Number(i)]);
  return s.trim();
}

export interface SqlBlockProps {
  sql: string | string[];
  /** 펼침 라벨 — 기본: "이 버튼이 실제로 실행한 SQL 보기" (P3 페르소나 문구) */
  label?: string;
  /** true면 미리보기(아직 실행 안 됨) warning 배지 표시 */
  preview?: boolean;
  /** 기본 펼침 여부 (SQL 투명 모드/전문가 모드 연동) */
  defaultOpen?: boolean;
  /** true면 한 줄 SQL을 복수 라인으로 포맷해 가독성 향상 (예: 챗봇 실행 GENERATE SQL) */
  format?: boolean;
}

export function SqlBlock({
  sql,
  label = "이 버튼이 실제로 실행한 SQL 보기",
  preview = false,
  defaultOpen = false,
  format = false,
}: SqlBlockProps) {
  const joined = Array.isArray(sql) ? sql.join("\n\n") : sql;
  const sqlText = format ? joined.split("\n\n").map(formatSql).join("\n\n") : joined;
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);

  // SQL 투명 모드 토글 시 기본 펼침 상태 동기화 (design 인터랙션 원칙 1)
  useEffect(() => setOpen(defaultOpen), [defaultOpen]);

  const copy = async () => {
    await navigator.clipboard.writeText(sqlText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="inline-flex cursor-pointer items-center gap-2 text-sm text-[var(--color-link)] hover:underline">
        {preview ? <StatusBadge status="warning">미리보기 — 아직 실행되지 않음</StatusBadge> : null}
        {label}
      </summary>
      <div className="relative mt-2">
        {/* 우상단 툴바 — 복사 (§5.6) */}
        <button
          onClick={copy}
          aria-label="SQL 복사"
          className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-[var(--radius-sm)] px-2 py-1 text-xs text-[var(--color-code-comment)] hover:bg-white/10 hover:text-[var(--color-code-text)]"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "복사됨" : "복사"}
        </button>
        <pre
          className="overflow-x-auto rounded-[var(--radius-lg)] p-4 pr-20 font-mono text-sm"
          style={{
            background: "var(--color-code-bg)",
            color: "var(--color-code-text)",
            lineHeight: "var(--leading-code)",
          }}
        >
          <code>{highlightSql(sqlText)}</code>
        </pre>
      </div>
    </details>
  );
}

export default SqlBlock;
