/**
 * API 타입 — 백엔드 Pydantic 스키마(docs/api-spec.md §11)와 1:1 대응.
 * 스캐폴딩 공유 계약 파일 — 변경은 api-spec 개정과 함께만.
 */

// ---------------------------------------------------------------- 공통

/** §1.3 모든 성공 응답의 공통 래퍼 */
export interface Envelope<T = unknown> {
  data: T;
  /** 실행 SQL 원문 배열 (비밀값은 ***MASKED***). OCI CLI 경로는 CLI 명령 원문 */
  executed_sql: string[];
  elapsed_ms: number;
}

/** §1.4 오류 envelope 본문 */
export interface ErrorBody {
  code: string;
  app_code: string;
  message_ko: string;
  hint_ko?: string | null;
  detail?: string | null;
  retryable: boolean;
  executed_sql: string[];
  docs_ref?: string | null;
  /** ADB_AMBIGUOUS(§2.7) 전용 */
  candidates?: AdbCandidate[] | null;
}

export interface ErrorResponse {
  error: ErrorBody;
}

// ---------------------------------------------------------------- connections

export interface WalletUploadResult {
  wallet_id: string;
  tns_aliases: string[];
  files_found: string[];
}

export interface WalletGenerateRequest {
  adb_name: string;
  wallet_password: string;
  compartment_id?: string; // 기본: TAEWAN.KIM 컴파트먼트 OCID
  oci_profile?: string;
  adb_ocid?: string | null;
}

export interface WalletGenerateResult extends WalletUploadResult {
  adb_ocid: string;
}

export interface AdbCandidate {
  adb_ocid: string;
  display_name: string;
  workload_type?: string | null;
}

export interface ConnectionCreate {
  name: string;
  wallet_id: string;
  tns_alias: string;
  username?: "admin" | "ADMIN";
  password: string;
  validate?: boolean;
}

export interface ConnectionUpdate {
  name?: string;
  tns_alias?: string;
  password?: string;
}

export type ConnectionStatus = "VALID" | "INVALID" | "UNKNOWN";

export interface ConnectionOut {
  id: string;
  name: string;
  tns_alias: string;
  username: string;
  db_version?: string | null;
  db_name?: string | null;
  status: ConnectionStatus;
  last_used_at?: string | null;
  created_at: string;
}

export interface ConnectionTestResult {
  ok: boolean;
  db_version?: string | null;
  latency_ms?: number | null;
  app_code?: string | null;
  message_ko?: string | null;
  hint_ko?: string | null;
}

// ---------------------------------------------------------------- privileges

export type CheckStatus = "pass" | "fail" | "not_applicable" | "unknown";

export interface PrivilegeCheck {
  check_id: string;
  title_ko: string;
  status: CheckStatus;
  description_ko: string;
  evidence_sql?: string | null;
  fix_sql?: string | null;
  remove_sql?: string | null; // 제거(해제) 미리보기 — resource_principal / credential
  docs_ref?: string | null;
}

/** ~/.oci/config 기반 User Principal 폼 기본값 (GET /privileges/oci-defaults) */
export interface OciCliDefaults {
  available: boolean;
  user_ocid?: string | null;
  tenancy_ocid?: string | null;
  fingerprint?: string | null;
  region?: string | null;
  key_file?: string | null;
  private_key?: string | null;
}

export interface PrivilegeCheckResult {
  provider: string;
  target_user: string;
  overall: "pass" | "action_required";
  checks: PrivilegeCheck[];
}

export interface CredentialSpec {
  credential_name: string;
  auth_type: "api_key" | "api_token" | "resource_principal";
  user_ocid?: string | null;
  tenancy_ocid?: string | null;
  private_key?: string | null;
  fingerprint?: string | null;
  username?: string | null;
  api_token?: string | null;
}

export interface PrivilegeApplyItem {
  check_id: string;
  operation?: "apply" | "remove";
  credential?: CredentialSpec | null;
  credential_name?: string | null; // remove 시 대상 credential 이름
  enable?: boolean | null;
}

export interface PrivilegeApplyRequest {
  provider?: string;
  target_user?: string;
  items: PrivilegeApplyItem[];
  recheck?: boolean;
}

export interface PrivilegeApplied {
  check_id: string;
  ok: boolean;
  executed_sql: string;
  error?: ErrorBody | null;
}

export interface PrivilegeApplyResult {
  applied: PrivilegeApplied[];
  recheck?: PrivilegeCheckResult | null;
}

// ---------------------------------------------------------------- profiles

export interface ObjectRef {
  owner: string;
  name?: string | null;
}

/** 레퍼런스 §3 검증 21개 속성 (R4 화이트리스트) */
export interface ProfileAttributes {
  provider?: string;
  credential_name?: string;
  object_list?: ObjectRef[] | null;
  object_list_mode?: "automated" | null;
  comments?: "true" | "false" | null;
  annotations?: "true" | "false" | null;
  constraints?: "true" | "false" | null;
  conversation?: "true" | "false" | null;
  temperature?: number | null;
  max_tokens?: number | null;
  model?: string;
  region?: string;
  oci_compartment_id?: string;
  oci_apiformat?: "GENERIC" | "COHERE" | null;
  oci_endpoint_id?: string | null;
  enforce_object_list?: "true" | "false" | null;
  case_sensitive_values?: "true" | "false" | null;
  target_language?: string | null;
  vector_index_name?: string | null;
  azure_resource_name?: string | null;
  azure_deployment_name?: string | null;
  provider_endpoint?: string | null;
}

export interface ProfileCreate {
  profile_name: string;
  attributes: ProfileAttributes;
  extra_attributes_json?: string | null;
}

export interface ProfileAttributeOut {
  name: string;
  value: string | null;
  verified: boolean;
  description_ko?: string | null;
  docs_ref?: string | null;
}

export interface ProfileDetail {
  profile_name: string;
  status: "ENABLED" | "DISABLED";
  attributes: ProfileAttributeOut[];
}

export interface ProfileSummary {
  profile_name: string;
  status: "ENABLED" | "DISABLED";
  provider?: string | null;
  model?: string | null;
  is_default: boolean;
}

export interface ProfileUpdate {
  attributes: Record<string, unknown>;
  preview_only?: boolean;
}

export interface DefaultProfileSetting {
  profile_name: string;
}

// ---------------------------------------------------------------- selectai

/** "showparameter"는 존재하지 않는 액션 — 정의 금지 */
export type SelectAIAction =
  | "runsql"
  | "showsql"
  | "explainsql"
  | "narrate"
  | "chat"
  | "showprompt"
  | "feedback"
  | "summarize"
  | "translate";

export interface GenerateRequest {
  prompt: string;
  action?: SelectAIAction;
  profile_name?: string | null;
  conversation_id?: string | null;
  row_limit?: number;
}

export interface GenerateResult {
  action: SelectAIAction;
  profile_name: string;
  result_type: "table" | "sql" | "text";
  generated_sql?: string | null;
  response_text?: string | null;
  columns?: string[] | null;
  rows?: unknown[][] | null;
  row_count?: number | null;
  truncated?: boolean | null;
}

export interface FeedbackRequest {
  profile_name: string;
  sql_id?: string | null;
  sql_text?: string | null;
  feedback_type: "positive" | "negative";
  response?: string | null;
  feedback_content?: string | null;
  operation?: "add" | "delete";
}

export interface ActionMeta {
  action: SelectAIAction;
  priority: "P0" | "P1" | "P2";
  title_ko: string;
  result_type: "table" | "sql" | "text";
  description_ko?: string;
}

export interface SuggestedPrompt {
  prompt: string;
  recommended_action: SelectAIAction;
  schema?: string;
  /** 데이터셋 — SH | OHV2 (프로파일 스코프 기반) */
  dataset?: "SH" | "OHV2";
  /** 난이도 분류 — 단순 | 복잡 | 분석 */
  category?: "단순" | "복잡" | "분석";
}

/** 프로파일 스코프 기반 추천 프롬프트 응답 */
export interface SuggestedPromptsResult {
  sh: boolean;
  ohv2: boolean;
  prompts: SuggestedPrompt[];
}

// ---------------------------------------------------------------- chat

export type ConversationAction = "runsql" | "showsql" | "explainsql" | "narrate" | "chat";

export interface ConversationCreate {
  title?: string;
  description?: string | null;
  retention_days?: number;
  conversation_length?: number;
}

export interface ConversationUpdate {
  title?: string | null;
  description?: string | null;
  retention_days?: number | null;
  conversation_length?: number | null;
}

export interface ConversationOut {
  conversation_id: string;
  title?: string | null;
  description?: string | null;
  retention_days?: number | null;
  conversation_length?: number | null;
}

export interface ChatMessageRequest {
  prompt: string;
  action?: ConversationAction;
  profile_name?: string | null;
}

export interface ChatMessageOut {
  prompt_id: string;
  prompt: string;
  response?: string | null;
  action?: string | null;
  created_at?: string | null;
}

export interface ChatCompareRequest {
  prompt: string;
  action?: ConversationAction;
  conversation_id: string;
  profile_name?: string | null;
}

export interface ChatCompareResult {
  without_context: GenerateResult;
  with_context: GenerateResult;
}

// ---------------------------------------------------------------- enrichment

export interface CommentEntry {
  table: string;
  column?: string | null;
  comment: string;
}

export interface CommentsApplyRequest {
  owner?: string;
  table_comment?: CommentEntry | null;
  column_comments?: CommentEntry[];
  preview_only?: boolean;
}

export interface DemoSchemaRequest {
  reset?: boolean;
}

export interface ProfilePairRequest {
  base_name?: string;
  object_list: ObjectRef[];
  annotations?: boolean;
  constraints?: boolean;
}

export interface EnrichCompareRequest {
  prompt: string;
  profile_off: string;
  profile_on: string;
  action?: "showsql" | "runsql";
  include_showprompt?: boolean;
}

export interface EnrichCompareSide {
  profile_name: string;
  generated_sql?: string | null;
  columns?: string[] | null;
  rows?: unknown[][] | null;
  error?: ErrorBody | null;
}

export interface EnrichCompareResult {
  prompt: string;
  before: EnrichCompareSide;
  after: EnrichCompareSide;
  augmented_prompt?: string | null;
}

// ---------------------------------------------------------------- schema / dashboard

export interface SchemaOwner {
  owner: string;
  is_current: boolean;
}

export interface SchemaOwnersResult {
  current_schema: string;
  owners: SchemaOwner[];
}

export interface TableInfo {
  owner?: string;
  table_name: string;
  comment?: string | null;
  num_rows?: number | null;
}

export interface ColumnInfo {
  column_name: string;
  data_type: string;
  nullable: boolean;
  comment?: string | null;
}

export type SignalStatus = "green" | "yellow" | "red";

export interface HealthSignal {
  id: string;
  status: SignalStatus;
  title_ko: string;
  detail_ko: string;
  fix_endpoint?: string | null;
}

export interface DashboardHealth {
  overall: SignalStatus;
  signals: HealthSignal[];
}

// ---------------------------------------------------------------- cleanup (resources)

export type CleanupResourceType =
  | "profile"
  | "credential"
  | "acl"
  | "conversation"
  | "demo_table"
  | "grant"
  | "wallet"
  | "connection"
  | "vector_index";

export interface CleanupLedgerItem {
  id: string;
  connection_id: string;
  resource_type: CleanupResourceType;
  resource_name: string;
  owner?: string | null;
  cleanup_order: number;
  cleanup_status: "pending" | "done" | "failed" | "skipped";
  cleanup_preview: string;
  created_at: string;
  cleaned_at?: string | null;
  last_error?: string | null;
}

export interface CleanupListResult {
  items: CleanupLedgerItem[];
  summary: Record<string, number>;
}

export interface CleanupRequest {
  item_ids?: string[] | null;
  resource_types?: CleanupResourceType[] | null;
  dry_run?: boolean;
  include_app_files?: boolean;
}

export interface CleanupItemResult {
  id: string;
  resource_type: CleanupResourceType;
  resource_name: string;
  ok: boolean;
  status: "done" | "failed" | "skipped" | "preview";
  cleanup_action?: string | null;
  error?: ErrorBody | null;
}

export interface CleanupResult {
  results: CleanupItemResult[];
  summary: Record<string, number>;
}
