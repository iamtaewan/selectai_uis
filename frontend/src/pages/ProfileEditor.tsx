/**
 * ProfileEditor 페이지 — PG-03a (/profiles/new · /profiles/:name/edit) / FR-04.
 * 좌: 검증 21개 속성 폼(그룹핑, GET /profiles/attribute-meta) /
 * 우: 해설 패널(필드 포커스 동기화 + 근거 페이지) + CREATE_PROFILE 실시간 미리보기
 *     (POST /profiles/preview — DB 미실행 정적 엔드포인트라 디바운스 자동 호출 허용).
 * object_list 브라우저: GET /schema/owners(is_current 기본 선택) → /schema/tables 체크박스
 * (검색 필터) → ObjectRef 배열. 미선택 시 생략 = "현재 스키마 전체 자동" (가이드 p78·p151).
 * JSON 직접 입력 토글(브라우저 선택과 양방향 동기화). 외부 공급자 선택 시 ACL 경고.
 * 설계 근거: design.md PG-03a, api-spec §4.1~§4.3·§4.6·§8.
 */
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ApiError, getEnvelope, patchEnvelope, postEnvelope } from "../api/client";
import type {
  ObjectRef,
  ProfileAttributes,
  ProfileDetail as ProfileDetailData,
  SchemaOwnersResult,
  TableInfo,
} from "../api/types";
import Button from "../components/Button";
import Panel from "../components/Panel";
import SqlBlock from "../components/SqlBlock";
import StatusBadge from "../components/StatusBadge";
import { useConnectionStore } from "../store/connectionStore";

// ---------------------------------------------------------------- 로컬 타입
// attribute-meta 응답 타입은 api/types.ts(공유 — 수정 금지)에 없어 페이지 로컬로 정의 (api-spec §4.1)
interface AttributeMetaItem {
  name: string;
  type: string;
  enum?: string[];
  deprecated?: string[];
  default?: string | null;
  required?: boolean;
  description_ko: string;
  docs_ref?: string | null;
  ui_group?: string;
}

interface AttributeMetaResult {
  verified_attributes: AttributeMetaItem[];
  defaults: Record<string, string>;
}

interface PreviewResult {
  sql_preview: string;
  warnings_ko: string[];
}

// ---------------------------------------------------------------- 그룹 정의
// 속성 그룹핑은 design.md PG-03a 절의 분류를 따른다 (ui_group 서버 값과 무관하게 화면 고정 — 가정)
const GROUPS: { title: string; attrs: string[] }[] = [
  { title: "기본 (필수)", attrs: ["provider", "credential_name", "model", "region", "oci_compartment_id"] },
  { title: "메타데이터 증강", attrs: ["comments", "annotations", "constraints"] },
  {
    title: "동작 제어",
    attrs: ["conversation", "temperature", "max_tokens", "enforce_object_list", "case_sensitive_values", "object_list_mode"],
  },
  {
    title: "공급자별",
    attrs: [
      "oci_apiformat",
      "oci_endpoint_id",
      "azure_resource_name",
      "azure_deployment_name",
      "provider_endpoint",
      "target_language",
      "vector_index_name",
    ],
  },
];

/** "true"/"false" 문자열 라디오 속성 (레퍼런스 §3 boolean_string 타입) */
const BOOLEAN_ATTRS = new Set([
  "comments",
  "annotations",
  "constraints",
  "conversation",
  "enforce_object_list",
  "case_sensitive_values",
]);

/** 공급자별 속성 표시 조건 — 선택한 provider에 따라 동적 표시 (design.md PG-03a) */
function providerAttrVisible(attr: string, provider: string): boolean {
  if (attr.startsWith("oci_")) return provider === "oci";
  if (attr.startsWith("azure_")) return provider === "azure";
  if (attr === "provider_endpoint") return provider !== "oci";
  return true; // target_language, vector_index_name 등은 항상 표시
}

const objectKey = (ref: ObjectRef) => `${ref.owner}.${ref.name ?? ""}`;

export function ProfileEditor() {
  const navigate = useNavigate();
  const { name: editName } = useParams<{ name: string }>();
  const isEdit = !!editName;
  const activeConnection = useConnectionStore((s) => s.activeConnection);

  // ---------------------------------------------------------------- 폼 상태
  const [profileName, setProfileName] = useState(editName ?? "");
  /** 21개 속성 값 — 폼은 전부 문자열로 보관, 전송 시 타입 변환 */
  const [values, setValues] = useState<Record<string, string>>({});
  const [selectedObjects, setSelectedObjects] = useState<ObjectRef[]>([]);
  const [extraJson, setExtraJson] = useState("");
  const [showExtraJson, setShowExtraJson] = useState(false);

  // object_list 브라우저 상태
  const [owner, setOwner] = useState<string>("");
  const [tableFilter, setTableFilter] = useState("");
  const [jsonMode, setJsonMode] = useState(false);
  const [objectListJson, setObjectListJson] = useState("[]");
  const [jsonParseError, setJsonParseError] = useState<string | null>(null);

  // 해설 패널 — 필드 포커스와 동기화 (design.md PG-03a 핵심 인터랙션)
  const [focusedAttr, setFocusedAttr] = useState<string>("object_list");

  // ---------------------------------------------------------------- 조회
  // 정적 메타데이터 — DB 미접속 (api-spec §1.2)
  const { data: meta } = useQuery({
    queryKey: ["profiles", "attribute-meta"],
    queryFn: async () => (await getEnvelope<AttributeMetaResult>("/profiles/attribute-meta")).data,
  });

  // 편집 모드 — 기존 속성 프리필 (GET /profiles/{name}, api-spec §4.5)
  const { data: existing } = useQuery({
    queryKey: ["profiles", editName],
    queryFn: async () =>
      (await getEnvelope<ProfileDetailData>(`/profiles/${encodeURIComponent(editName!)}`)).data,
    enabled: isEdit,
  });

  // 스키마 브라우저 — 인증 사용자가 DB에서 볼 수 있는 것만 (ALL_* 뷰, api-spec §8)
  const { data: ownersResult } = useQuery({
    queryKey: ["schema", "owners"],
    queryFn: async () => (await getEnvelope<SchemaOwnersResult>("/schema/owners")).data,
    enabled: !!activeConnection,
  });

  const { data: tables, isLoading: tablesLoading } = useQuery({
    queryKey: ["schema", "tables", owner],
    queryFn: async () => (await getEnvelope<TableInfo[]>("/schema/tables", { owner })).data,
    enabled: !!activeConnection && !!owner,
  });

  // 기본값 자동 채움 — provider=oci, model, region, 컴파트먼트, credential (design.md PG-03a)
  useEffect(() => {
    if (!meta || isEdit) return;
    setValues((prev) => (Object.keys(prev).length > 0 ? prev : { ...meta.defaults }));
  }, [meta, isEdit]);

  // 편집 모드 프리필
  useEffect(() => {
    if (!existing) return;
    const next: Record<string, string> = {};
    for (const attr of existing.attributes) {
      if (attr.name === "object_list") {
        // object_list 속성 값은 JSON 문자열 — 파싱 실패 시 빈 선택 유지
        try {
          const parsed = JSON.parse(attr.value ?? "[]") as ObjectRef[];
          if (Array.isArray(parsed)) setSelectedObjects(parsed);
        } catch {
          /* 무시 — JSON 직접 입력으로 보정 가능 */
        }
      } else if (attr.value != null) {
        next[attr.name] = attr.value;
      }
    }
    setValues(next);
  }, [existing]);

  // is_current=true 스키마를 기본 선택 (api-spec §8.1)
  useEffect(() => {
    if (ownersResult && !owner) setOwner(ownersResult.current_schema);
  }, [ownersResult, owner]);

  // 브라우저 선택 ↔ JSON 직접 입력 양방향 동기화 (브라우저 → JSON)
  useEffect(() => {
    if (!jsonMode) setObjectListJson(JSON.stringify(selectedObjects, null, 2));
  }, [selectedObjects, jsonMode]);

  // ---------------------------------------------------------------- 페이로드 조립
  const provider = values.provider ?? "oci";

  const attributes = useMemo<ProfileAttributes>(() => {
    const v = (k: string) => (values[k]?.trim() ? values[k].trim() : undefined);
    const b = (k: string) => {
      const raw = v(k);
      return raw === "true" || raw === "false" ? (raw as "true" | "false") : undefined;
    };
    const attrs: ProfileAttributes = {
      provider: v("provider"),
      credential_name: v("credential_name"),
      model: v("model"),
      region: v("region"),
      oci_compartment_id: v("oci_compartment_id"),
      comments: b("comments") ?? null,
      annotations: b("annotations") ?? null,
      constraints: b("constraints") ?? null,
      conversation: b("conversation") ?? null,
      enforce_object_list: b("enforce_object_list") ?? null,
      case_sensitive_values: b("case_sensitive_values") ?? null,
      temperature: v("temperature") != null ? Number(values.temperature) : null,
      max_tokens: v("max_tokens") != null ? Number(values.max_tokens) : null,
      object_list_mode: v("object_list_mode") === "automated" ? "automated" : null,
      oci_apiformat:
        v("oci_apiformat") === "GENERIC" || v("oci_apiformat") === "COHERE"
          ? (values.oci_apiformat as "GENERIC" | "COHERE")
          : null,
      oci_endpoint_id: v("oci_endpoint_id") ?? null,
      target_language: v("target_language") ?? null,
      vector_index_name: v("vector_index_name") ?? null,
      azure_resource_name: v("azure_resource_name") ?? null,
      azure_deployment_name: v("azure_deployment_name") ?? null,
      provider_endpoint: v("provider_endpoint") ?? null,
      // 미선택 시 object_list 생략 → "현재 스키마 전체 자동 선택" (가이드 p78·p151)
      object_list: selectedObjects.length > 0 ? selectedObjects : null,
    };
    return attrs;
  }, [values, selectedObjects]);

  // ---------------------------------------------------------------- 실시간 미리보기
  const [preview, setPreview] = useState<PreviewResult | null>(null);

  const previewMutation = useMutation({
    mutationFn: async () =>
      (
        await postEnvelope<PreviewResult>("/profiles/preview", {
          profile_name: profileName || "PROFILE_NAME",
          attributes,
          extra_attributes_json: extraJson.trim() || null,
        })
      ).data,
    onSuccess: setPreview,
  });

  // 입력 변경 500ms 디바운스 — preview는 실행 없는 정적 변환이라 자동 호출 허용 (api-spec §4.2)
  const previewMutate = previewMutation.mutate;
  useEffect(() => {
    const t = setTimeout(() => previewMutate(), 500);
    return () => clearTimeout(t);
  }, [profileName, attributes, extraJson, previewMutate]);

  // ---------------------------------------------------------------- 생성/수정
  const saveMutation = useMutation({
    mutationFn: async () => {
      if (isEdit) {
        // 편집 = SET_ATTRIBUTES (api-spec §4.6) — 조립한 속성 객체를 그대로 전달
        return patchEnvelope(`/profiles/${encodeURIComponent(editName!)}`, {
          attributes,
          preview_only: false,
        });
      }
      return postEnvelope("/profiles", {
        profile_name: profileName,
        attributes,
        extra_attributes_json: extraJson.trim() || null,
      });
    },
    onSuccess: () => navigate("/profiles"),
  });

  const saveError = saveMutation.error instanceof ApiError ? saveMutation.error.body : null;

  // ---------------------------------------------------------------- 헬퍼
  const metaByName = useMemo(() => {
    const map = new Map<string, AttributeMetaItem>();
    meta?.verified_attributes.forEach((a) => map.set(a.name, a));
    return map;
  }, [meta]);

  const setValue = (name: string, value: string) =>
    setValues((prev) => ({ ...prev, [name]: value }));

  const toggleObject = (ref: ObjectRef) => {
    setSelectedObjects((prev) => {
      const key = objectKey(ref);
      return prev.some((o) => objectKey(o) === key)
        ? prev.filter((o) => objectKey(o) !== key)
        : [...prev, ref];
    });
  };

  const filteredTables = (tables ?? []).filter((t) =>
    t.table_name.toLowerCase().includes(tableFilter.toLowerCase()),
  );

  const focusedMeta = metaByName.get(focusedAttr);

  /** 공통 폼 필드 렌더 — enum=select / boolean_string=라디오 / 그 외 input */
  const renderAttrField = (name: string): ReactNode => {
    const m = metaByName.get(name);
    const value = values[name] ?? "";
    const common = {
      id: `attr-${name}`,
      onFocus: () => setFocusedAttr(name),
      className:
        "h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2 text-sm",
    };
    let control: ReactNode;
    if (BOOLEAN_ATTRS.has(name)) {
      control = (
        <div className="flex h-9 items-center gap-4 text-sm" onFocus={() => setFocusedAttr(name)}>
          {["", "false", "true"].map((opt) => (
            <label key={opt || "unset"} className="flex cursor-pointer items-center gap-1">
              <input
                type="radio"
                name={`attr-${name}`}
                checked={value === opt}
                onChange={() => setValue(name, opt)}
                onFocus={() => setFocusedAttr(name)}
              />
              {opt === "" ? "미지정" : opt}
            </label>
          ))}
        </div>
      );
    } else if (m?.enum && m.enum.length > 0) {
      control = (
        <select {...common} value={value} onChange={(e) => setValue(name, e.target.value)}>
          <option value="">(미지정)</option>
          {m.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
              {m.deprecated?.includes(opt) ? " (deprecated)" : ""}
            </option>
          ))}
        </select>
      );
    } else {
      control = (
        <input
          {...common}
          type={name === "temperature" || name === "max_tokens" ? "number" : "text"}
          step={name === "temperature" ? "0.1" : undefined}
          value={value}
          onChange={(e) => setValue(name, e.target.value)}
        />
      );
    }
    return (
      <div key={name} className="flex flex-col gap-1">
        <label htmlFor={`attr-${name}`} className="flex items-center gap-1 text-sm font-medium">
          {name}
          {m?.required ? <span className="text-[var(--color-danger)]">*</span> : null}
          <button
            type="button"
            aria-label={`${name} 해설 보기`}
            title={m?.description_ko ?? ""}
            className="text-[var(--color-info)]"
            onClick={() => setFocusedAttr(name)}
          >
            ⓘ
          </button>
          {m?.deprecated?.includes(value) ? <StatusBadge status="warning">deprecated</StatusBadge> : null}
        </label>
        {control}
      </div>
    );
  };

  // ---------------------------------------------------------------- 렌더
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold">{isEdit ? `프로파일 편집 — ${editName}` : "새 프로파일"}</h2>
        <p className="mt-1 text-sm text-[var(--color-neutral-60)]">
          폼 입력이 곧 CREATE_PROFILE PL/SQL입니다 — 우측 미리보기가 실시간 동기화됩니다.
        </p>
      </div>

      <div className="grid grid-cols-[55%_45%] gap-6">
        {/* ---------------------------------- 좌: 입력 폼 */}
        <div className="flex flex-col gap-5">
          <Panel>
            <div className="flex flex-col gap-1">
              <label htmlFor="profile-name" className="text-sm font-medium">
                프로파일 이름
              </label>
              <input
                id="profile-name"
                className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2 text-sm"
                value={profileName}
                readOnly={isEdit}
                onChange={(e) => setProfileName(e.target.value.toUpperCase())}
                placeholder="GENAI_SH"
              />
            </div>
          </Panel>

          {/* 외부 공급자 → ACL 경고 (FR-03 연동) */}
          {provider && provider !== "oci" ? (
            <div className="rounded-[var(--radius-md)] bg-[var(--color-warning-tint)] p-3 text-sm">
              ⚠ 외부 공급자({provider})는 네트워크 ACL이 필요합니다.{" "}
              <button className="text-[var(--color-link)] underline" onClick={() => navigate("/permissions")}>
                권한 점검으로 이동 →
              </button>
            </div>
          ) : null}

          {/* 속성 그룹 — 기본/대상 객체/메타데이터 증강/동작 제어/공급자별/고급 JSON */}
          {GROUPS.map((group) => {
            const visibleAttrs =
              group.title === "공급자별"
                ? group.attrs.filter((a) => providerAttrVisible(a, provider))
                : group.attrs;
            if (visibleAttrs.length === 0) return null;
            return (
              <Panel key={group.title} title={`▾ ${group.title}`}>
                <div className="grid grid-cols-2 gap-4">{visibleAttrs.map(renderAttrField)}</div>

                {/* 기본 그룹 뒤에 대상 객체 브라우저 삽입 */}
                {group.title === "기본 (필수)" ? null : null}
              </Panel>
            );
          })}

          {/* ▾ 대상 객체 (object_list) — 스키마/테이블 브라우저 (FR-04 핵심) */}
          <Panel title="▾ 대상 객체 (object_list)">
            <div onFocus={() => setFocusedAttr("object_list")}>
              {!activeConnection ? (
                <p className="text-sm text-[var(--color-neutral-60)]">
                  커넥션이 없어 스키마를 조회할 수 없습니다 — 연결 후 선택하거나 JSON으로 직접 입력하세요.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-3">
                    <label htmlFor="owner-select" className="text-sm font-medium">
                      스키마
                    </label>
                    <select
                      id="owner-select"
                      className="h-9 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2 text-sm"
                      value={owner}
                      onChange={(e) => setOwner(e.target.value)}
                    >
                      {(ownersResult?.owners ?? []).map((o) => (
                        <option key={o.owner} value={o.owner}>
                          {o.owner}
                          {o.is_current ? " (현재 스키마)" : ""}
                        </option>
                      ))}
                    </select>
                    <input
                      aria-label="테이블 검색"
                      className="h-9 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] px-2 text-sm"
                      placeholder="테이블 검색…"
                      value={tableFilter}
                      onChange={(e) => setTableFilter(e.target.value)}
                    />
                    <button
                      className="text-sm text-[var(--color-link)] underline"
                      onClick={() => {
                        // 필터된 목록 전체 선택 (이미 선택된 항목은 유지)
                        const refs = filteredTables.map((t) => ({
                          owner: t.owner ?? owner,
                          name: t.table_name,
                        }));
                        setSelectedObjects((prev) => {
                          const keys = new Set(prev.map(objectKey));
                          return [...prev, ...refs.filter((r) => !keys.has(objectKey(r)))];
                        });
                      }}
                    >
                      전체 선택
                    </button>
                  </div>

                  <div className="mt-3 max-h-56 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--color-neutral-30)] p-2">
                    {tablesLoading ? (
                      <p className="text-sm text-[var(--color-running)]">테이블 조회 중…</p>
                    ) : filteredTables.length === 0 ? (
                      <p className="text-sm text-[var(--color-neutral-60)]">
                        표시할 테이블이 없습니다. 다른 스키마를 선택하거나 데모 스키마 셋업(증강 비교 ①)을 이용하세요.
                      </p>
                    ) : (
                      <ul className="grid grid-cols-2 gap-1">
                        {filteredTables.map((t) => {
                          const ref: ObjectRef = { owner: t.owner ?? owner, name: t.table_name };
                          const checked = selectedObjects.some((o) => objectKey(o) === objectKey(ref));
                          return (
                            <li key={objectKey(ref)}>
                              <label className="flex cursor-pointer items-center gap-2 text-sm">
                                <input type="checkbox" checked={checked} onChange={() => toggleObject(ref)} />
                                <code>
                                  {ref.owner}.{ref.name}
                                </code>
                                {t.num_rows != null ? (
                                  <span className="text-xs text-[var(--color-neutral-50)]">{t.num_rows}행</span>
                                ) : null}
                              </label>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </>
              )}

              {/* 선택 요약 + 미선택 안내 */}
              <p className="mt-2 text-xs text-[var(--color-neutral-60)]">
                {selectedObjects.length > 0
                  ? `선택 ${selectedObjects.length}개 — 여러 스키마의 테이블을 섞어 담을 수 있습니다.`
                  : "아무것도 선택하지 않으면 object_list를 생략합니다 → 현재 스키마 전체가 자동 선택됩니다 (가이드 p78·p151). 테이블을 좁힐수록 정확도가 올라갑니다."}
              </p>

              {/* JSON 직접 입력 토글 — 양방향 동기화 고급 경로 */}
              <button
                className="mt-2 text-sm text-[var(--color-link)] underline"
                onClick={() => setJsonMode((v) => !v)}
              >
                {jsonMode ? "브라우저 선택으로 전환" : "JSON 직접 입력으로 전환"}
              </button>
              {jsonMode ? (
                <div className="mt-2">
                  <textarea
                    aria-label="object_list JSON"
                    rows={6}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] p-2 font-mono text-xs"
                    value={objectListJson}
                    onChange={(e) => {
                      setObjectListJson(e.target.value);
                      try {
                        const parsed = JSON.parse(e.target.value) as ObjectRef[];
                        if (Array.isArray(parsed)) {
                          setSelectedObjects(parsed.filter((o) => o && typeof o.owner === "string"));
                          setJsonParseError(null);
                        }
                      } catch {
                        setJsonParseError("JSON 파싱 오류 — [{\"owner\": \"SH\", \"name\": \"customers\"}] 형식이어야 합니다.");
                      }
                    }}
                  />
                  {jsonParseError ? (
                    <p className="text-xs text-[var(--color-danger)]">{jsonParseError}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          </Panel>

          {/* ▾ 고급 — JSON 직접 입력 (미검증 속성 격리, R4) */}
          <Panel title="▾ 고급 — JSON 직접 입력 ⚠">
            <button
              className="text-sm text-[var(--color-link)] underline"
              onClick={() => setShowExtraJson((v) => !v)}
            >
              {showExtraJson ? "닫기" : "열기"}
            </button>
            {showExtraJson ? (
              <div className="mt-2">
                <p className="mb-1 text-xs text-[var(--color-warning)]">
                  이 가이드에서 검증되지 않은 속성은 오류가 발생할 수 있습니다. 검증 21개 속성과 키가 충돌하면
                  거부됩니다 (ATTRIBUTE_CONFLICT).
                </p>
                <textarea
                  aria-label="미검증 속성 JSON"
                  rows={4}
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--color-neutral-40)] bg-[var(--color-neutral-0)] p-2 font-mono text-xs"
                  value={extraJson}
                  onChange={(e) => setExtraJson(e.target.value)}
                  placeholder='{"some_attr": "value"}'
                />
              </div>
            ) : null}
          </Panel>
        </div>

        {/* ---------------------------------- 우: 해설 패널 + SQL 미리보기 */}
        <div className="flex flex-col gap-5">
          <Panel variant="explain" title={`▣ 지금 선택한 속성: ${focusedAttr}`}>
            {focusedAttr === "object_list" ? (
              <p>
                NL2SQL 대상 객체의 JSON 배열입니다. 미지정 시 현재 스키마 전체가 자동 선택됩니다. 테이블을
                좁힐수록 정확도가 올라갑니다.
                <span className="mt-1 block text-xs text-[var(--color-info)]">근거: 가이드 p78, p151</span>
              </p>
            ) : focusedMeta ? (
              <p>
                {focusedMeta.description_ko}
                {focusedMeta.docs_ref ? (
                  <span className="mt-1 block text-xs text-[var(--color-info)]">근거: {focusedMeta.docs_ref}</span>
                ) : null}
              </p>
            ) : (
              <p>필드를 클릭하거나 포커스하면 해당 속성의 한국어 해설이 여기에 표시됩니다.</p>
            )}
          </Panel>

          <Panel
            title={
              <span className="flex items-center justify-between">
                <span>▣ CREATE_PROFILE 미리보기</span>
                {preview ? (
                  <button
                    className="text-xs font-normal text-[var(--color-link)] underline"
                    onClick={() => void navigator.clipboard.writeText(preview.sql_preview)}
                  >
                    복사
                  </button>
                ) : null}
              </span>
            }
          >
            {preview ? (
              <>
                <SqlBlock defaultOpen preview label="입력과 실시간 동기화" sql={preview.sql_preview} />
                {preview.warnings_ko.length > 0 ? (
                  <ul className="mt-2 flex flex-col gap-1">
                    {preview.warnings_ko.map((w) => (
                      <li key={w} className="text-xs text-[var(--color-warning)]">
                        ⚠ {w}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="text-sm text-[var(--color-neutral-60)]">입력을 시작하면 PL/SQL이 여기에 표시됩니다.</p>
            )}
          </Panel>

          {/* 생성 실패 — ORA 원문 + 한국어 해설 + 폼 값 보존 (상태: 오류) */}
          {saveError ? (
            <Panel variant="explain">
              <p className="text-sm font-medium text-[var(--color-danger)]">{saveError.message_ko}</p>
              {saveError.hint_ko ? (
                <p className="mt-1 text-sm text-[var(--color-neutral-70)]">→ {saveError.hint_ko}</p>
              ) : null}
              {saveError.detail ? (
                <details className="mt-1">
                  <summary className="cursor-pointer text-xs text-[var(--color-neutral-60)]">오류 원문 보기</summary>
                  <pre className="whitespace-pre-wrap text-xs">{saveError.detail}</pre>
                </details>
              ) : null}
              {saveError.app_code === "INSUFFICIENT_PRIVILEGE" ? (
                <Button variant="secondary" className="mt-2" onClick={() => navigate("/permissions")}>
                  권한 점검으로 이동
                </Button>
              ) : null}
            </Panel>
          ) : null}

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => navigate("/profiles")}>
              취소
            </Button>
            <Button
              onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}
              disabled={!isEdit && !profileName}
            >
              {isEdit ? "변경 사항 적용" : "프로파일 생성"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileEditor;
