# API 명세 — Select AI Demo Studio Backend (FastAPI)

| 항목 | 내용 |
|---|---|
| 문서 | api-spec.md v1.0 (2026-06-12) |
| 작성자 | 백엔드 API 엔지니어 (전문가 6/8) |
| 상위 문서 | `PRD.md` (FR-01~FR-10), `docs/research/selectai-reference.md` (기술 근거 단일 소스) |
| 스택 | Python FastAPI + python-oracledb (Thin, mTLS wallet) |
| 대상 DB | OCI Autonomous AI Database 26ai, 사용자 `admin` |

> **아키텍처 원칙 (PRD §6, 리스크 R3 — 위반 금지)**
> 백엔드는 커넥션 풀 기반 **stateless**다. 세션 상태에 의존하는 `SELECT AI` 키워드, `DBMS_CLOUD_AI.SET_PROFILE`, `SET_CONVERSATION_ID`는 **어떤 엔드포인트에서도 사용하지 않는다**. 모든 Select AI 실행은 단일 패턴을 따른다 (레퍼런스 §2, p42·p129):
>
> ```sql
> SELECT DBMS_CLOUD_AI.GENERATE(
>          prompt       => :prompt,
>          profile_name => :profile_name,
>          action       => :action,
>          params       => :params_json   -- 예: '{"conversation_id":"<uuid>"}'
>        ) AS response FROM dual;
> ```
>
> 또한 `showparameter`라는 액션은 존재하지 않으므로(레퍼런스 §1) API 어디에도 노출하지 않는다. 프로파일 속성 조회는 `USER/DBA_CLOUD_AI_PROFILE_ATTRIBUTES` 뷰를 사용한다.

---

## 1. 공통 규약

### 1.1 Base Path / 콘텐츠 타입

- Base path: **`/api/v1`**
- 요청/응답 본문: `application/json; charset=utf-8` (wallet 업로드만 `multipart/form-data`)
- 모든 응답 메시지·해설 필드는 한국어, 코드/SQL/식별자는 영어.

### 1.2 커넥션 컨텍스트

DB를 사용하는 모든 엔드포인트(§3 privileges 이후 전부)는 대상 커넥션을 **HTTP 헤더로** 받는다. 단, 정적 메타데이터 엔드포인트(`/profiles/attribute-meta`, `/selectai/actions`, `/selectai/suggested-prompts`)는 DB를 조회하지 않으므로 헤더가 없어도 된다.

```
X-Connection-Id: conn_8f2a1c
```

- 헤더 누락 시: `400 CONNECTION_REQUIRED`
- 존재하지 않는 ID: `404 CONNECTION_NOT_FOUND`
- 해당 커넥션 풀이 닫혀 있으면 lazy 재생성 후 처리.

### 1.3 성공 응답 공통 필드

학습 효과 요구사항(PRD 페르소나 P3, FR 수용 기준 "실행 SQL 미리보기/펼침 노출")에 따라, **DB에서 SQL/PLSQL을 실행한 모든 응답은 실행 원문을 포함**한다.

```json
{
  "data": { "...리소스별 페이로드..." },
  "executed_sql": [
    "SELECT DBMS_CLOUD_AI.GENERATE(prompt => :1, profile_name => :2, action => :3) FROM dual"
  ],
  "elapsed_ms": 4210
}
```

- `executed_sql`: 실제 실행된 문장 배열(실행 순서대로). 바인드 변수는 `:1` 형태 그대로 노출하되, **비밀번호·private_key 등 비밀 값은 `***MASKED***`로 치환**한다.
- `elapsed_ms`: 서버 측 총 처리 시간 (FR-06 latency 표시용).

### 1.4 오류 응답 포맷

HTTP status는 4xx/5xx, 본문은 단일 포맷:

```json
{
  "error": {
    "code": "ORA-20000",
    "app_code": "DATA_ACCESS_DISABLED",
    "message_ko": "Select AI의 데이터 액세스가 비활성화되어 있어 narrate/합성 데이터를 실행할 수 없습니다.",
    "hint_ko": "권한 점검 화면에서 'Data Access 활성화' 버튼을 눌러 ENABLE_DATA_ACCESS를 적용한 뒤 다시 시도하세요.",
    "detail": "ORA-20000: Data access is disabled for SELECT AI",
    "retryable": false,
    "executed_sql": ["SELECT DBMS_CLOUD_AI.GENERATE(...) FROM dual"],
    "docs_ref": "selectai-reference.md §2 데이터 액세스 제어 (p174-176)"
  }
}
```

| 필드 | 설명 |
|---|---|
| `code` | 원본 오류 코드 (`ORA-xxxxx`, `DPY-xxxx`) 또는 앱 정의 코드 |
| `app_code` | 프론트엔드 분기용 안정 식별자 (대문자 스네이크) |
| `message_ko` | 사용자(비개발자 포함) 친화 한국어 메시지 |
| `hint_ko` | 다음 행동 안내 — 가능하면 복구 버튼/화면을 지목 |
| `detail` | 원본 오류 메시지 원문 (펼침 영역 표시용) |
| `retryable` | 재시도 버튼 노출 여부 (LLM 환각/일시 오류 = true) |
| `docs_ref` | 레퍼런스 문서 근거 (학습 효과) |

### 1.5 Oracle 오류 → 사용자 메시지 변환 규칙

백엔드는 `oracledb.DatabaseError`를 가로채 아래 매핑 테이블로 변환한다. 매핑에 없는 오류는 `app_code: "ORACLE_ERROR"` + 원문 노출.

| 원본 코드 | app_code | HTTP | message_ko (요지) | retryable |
|---|---|---|---|---|
| `ORA-01017` | `INVALID_CREDENTIALS` | 401 | admin 비밀번호가 올바르지 않습니다 | false |
| `DPY-6005` / `ORA-12506` 등 네트워크 | `DB_UNREACHABLE` | 502 | DB에 연결할 수 없습니다. wallet/TNS alias/네트워크를 확인하세요 | true |
| `ORA-28759` / wallet 파일 오류 | `WALLET_INVALID` | 400 | wallet 파일을 열 수 없습니다. ADB 콘솔에서 wallet을 다시 다운로드하세요 | false |
| `ORA-00923` | `PROFILE_NOT_SET` | 400 | 프로파일 없이 SELECT AI가 실행되었습니다 — 백엔드 버그(세션 상태 의존 코드 혼입) 가능성. GENERATE 패턴 위반 점검 필요 (레퍼런스 §1 p45) | false |
| `ORA-20000` (`Data access is disabled`) | `DATA_ACCESS_DISABLED` | 409 | Data Access가 비활성 상태입니다 (narrate/합성 데이터 차단) | false |
| `ORA-00942` | `OBJECT_NOT_FOUND` | 404 | 생성된 SQL이 존재하지 않는 테이블을 참조했습니다 (LLM 환각 가능, p14·p45) | true |
| `ORA-00904` / `ORA-00936` 등 SQL 문법 | `GENERATED_SQL_INVALID` | 422 | LLM이 생성한 SQL이 유효하지 않습니다. 프롬프트를 구체화하거나 comments 증강을 활성화해 보세요 | true |
| `ORA-01031` | `INSUFFICIENT_PRIVILEGE` | 403 | 권한이 부족합니다. 권한 점검 화면에서 누락 항목을 적용하세요 | false |
| `ORA-20404` 등 profile not found 계열 | `PROFILE_NOT_FOUND` | 404 | 지정한 프로파일이 존재하지 않습니다 | false |
| 호출 타임아웃 (`call_timeout` 초과, DPY-4011 등) | `LLM_TIMEOUT` | 504 | AI 응답이 제한 시간을 초과했습니다. 다시 시도하세요 | true |

추가 규칙:

1. **PL/SQL 래퍼 메시지 박리**: `ORA-06512` 스택 라인은 `detail`에만 남기고 `message_ko` 생성에는 최상위 `ORA-` 코드만 사용.
2. **비밀 마스킹**: 오류 메시지/`executed_sql`에 비밀번호, `private_key`, API 키가 포함되면 `***MASKED***` 치환 후 응답·로그 기록 (PRD R5). OCI CLI 명령을 노출하는 경우(§2.7)도 동일 — `--password` 값은 `***MASKED***`.
3. **LLM 환각 계열**(`OBJECT_NOT_FOUND`, `GENERATED_SQL_INVALID`)은 `retryable: true` + `hint_ko`에 "재시도" 또는 "comments 증강 시연(FR-08)" 유도 문구.

### 1.6 프롬프트 이스케이프

`GENERATE`는 바인드 변수로 호출하므로 SQL 인젝션·따옴표 문제에서 자유롭다. 단, **SQL 미리보기 문자열 생성 시**에는 작은따옴표를 `''`로 이스케이프해 표시한다 (레퍼런스 §1 p45, FR-06 수용 기준).

---

## 2. Connections — DB 연결/커넥션 관리 (FR-01, FR-02)

### 2.1 `POST /api/v1/connections/wallet` — wallet zip 업로드 + TNS alias 추출

- **요청**: `multipart/form-data`
  - `file`: wallet zip (필수, 최대 5 MB)
- **처리**: 서버 임시 영역에 압축 해제 → `tnsnames.ora`/`ewallet.pem`(또는 `cwallet.sso`) 존재 검증 → alias 파싱 → 암호화 보관 후 `wallet_id` 발급. (저장 방식·암호화 키 관리는 오픈 이슈 O2 — `architecture.md` 결정에 따름)
- **응답 200**:

```json
{
  "data": {
    "wallet_id": "wlt_3f9d2a",
    "tns_aliases": ["demoadb_high", "demoadb_medium", "demoadb_low", "demoadb_tp", "demoadb_tpurgent"],
    "files_found": ["tnsnames.ora", "sqlnet.ora", "ewallet.pem"]
  },
  "executed_sql": [],
  "elapsed_ms": 120
}
```

- **오류**: `400 WALLET_INVALID` (zip 아님 / tnsnames.ora 누락 / 손상), `413 FILE_TOO_LARGE`.

### 2.2 `POST /api/v1/connections` — 커넥션 생성(검증 포함)

- **요청**:

```json
{
  "name": "고객사A PoC ADB",
  "wallet_id": "wlt_3f9d2a",
  "tns_alias": "demoadb_high",
  "username": "admin",
  "password": "********",
  "validate": true
}
```

- **처리**: `validate=true`(기본)면 python-oracledb로 즉시 접속 테스트 후 저장. 비밀번호는 서버 측 암호화 저장(R5, O2). `username`은 v1에서 `admin` 고정 — 다른 값이면 `400 ADMIN_ONLY`.
- **검증 시 내부 SQL**:

```sql
SELECT banner_full FROM v$version WHERE ROWNUM = 1;
SELECT sys_context('USERENV','CURRENT_USER')  AS current_user,
       sys_context('USERENV','DB_NAME')       AS db_name,
       sys_context('USERENV','SERVICE_NAME')  AS service_name
  FROM dual;
```

- **응답 201**:

```json
{
  "data": {
    "id": "conn_8f2a1c",
    "name": "고객사A PoC ADB",
    "tns_alias": "demoadb_high",
    "username": "ADMIN",
    "db_version": "Oracle AI Database 26ai ...",
    "db_name": "DEMOADB",
    "status": "VALID",
    "last_used_at": null,
    "created_at": "2026-06-12T10:00:00+09:00"
  },
  "executed_sql": ["SELECT banner_full FROM v$version WHERE ROWNUM = 1", "..."],
  "elapsed_ms": 1840
}
```

- **오류**: `401 INVALID_CREDENTIALS`, `502 DB_UNREACHABLE`, `409 CONNECTION_NAME_EXISTS`.

### 2.3 `GET /api/v1/connections` — 목록

응답에 비밀번호/wallet 내용 미포함. `last_used_at` 내림차순 정렬 → 프론트가 첫 항목을 기본 선택 (FR-02 "마지막 사용 커넥션").

```json
{ "data": [ { "id": "conn_8f2a1c", "name": "고객사A PoC ADB", "tns_alias": "demoadb_high",
              "username": "ADMIN", "status": "VALID", "last_used_at": "2026-06-12T09:55:00+09:00" } ],
  "executed_sql": [], "elapsed_ms": 3 }
```

### 2.4 `POST /api/v1/connections/{id}/test` — 연결 테스트

- 서버 측 타임아웃 **5초** (FR-02 수용 기준). `oracledb` `tcp_connect_timeout` + `call_timeout` 적용.
- **응답 200**: `{ "data": { "ok": true, "db_version": "...", "latency_ms": 420 }, ... }`
- **실패 시에도 200으로 진단 결과 반환** (테스트 행위 자체는 성공):

```json
{ "data": { "ok": false, "app_code": "DB_UNREACHABLE",
            "message_ko": "5초 내에 DB에 연결하지 못했습니다.",
            "hint_ko": "ADB 인스턴스가 STOPPED 상태인지 OCI 콘솔에서 확인하세요." },
  "executed_sql": ["SELECT 1 FROM dual"], "elapsed_ms": 5003 }
```

### 2.5 `DELETE /api/v1/connections/{id}` — 삭제

- 커넥션 풀 종료 → 저장된 자격/연결 메타 삭제. wallet은 다른 커넥션이 참조하지 않을 때만 삭제.
- **응답 204**. 오류: `404 CONNECTION_NOT_FOUND`.

### 2.6 `PATCH /api/v1/connections/{id}` — 수정(이름/비밀번호/alias 교체)

요청 필드는 모두 optional. 비밀번호 변경 시 재검증 수행. 응답은 2.2와 동일 스키마.

### 2.7 `POST /api/v1/connections/wallet/generate` — wallet 자동 다운로드 (OCI CLI)

wallet zip이 없는 시연자를 위한 §2.1의 대체 경로 (FR-01 하위 기능 "Wallet 자동 다운로드"). 백엔드가 시연자 로컬의 **OCI CLI를 subprocess로 호출**해 지정 컴파트먼트·ADB 표시 이름으로 wallet을 내려받고, 이후는 §2.1 업로드 경로와 **동일하게 합류**한다 (압축 해제 → `tnsnames.ora` 파싱 → alias 반환). 저장 위치는 `~/.selectai/wallets/{wallet_id}/` (architecture.md §3.1.1).

- **사전 조건**: OCI CLI 설치 + `~/.oci/config` 인증 구성 (앱이 관리하지 않음 — security.md §2.5).
- **요청**:

```json
{
  "adb_name": "DEMOADB",
  "wallet_password": "********",
  "compartment_id": "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq",
  "oci_profile": "DEFAULT",
  "adb_ocid": null
}
```

  - `compartment_id` (옵션): 기본값 TAEWAN.KIM 컴파트먼트 OCID (CLAUDE.md 전역 규칙 — 모든 OCI 작업은 TAEWAN.KIM 컴파트먼트).
  - `oci_profile` (옵션): 기본 `DEFAULT`.
  - `adb_ocid` (옵션): 복수 매칭 후 사용자가 후보를 선택해 재호출할 때 지정 — 지정 시 ① 조회를 건너뛴다.
- **내부 CLI 호출** (순서대로):

```bash
# ① ADB OCID 조회 (0건/복수 건 오류 처리)
oci db autonomous-database list --compartment-id <ocid> --display-name <adb_name> --lifecycle-state AVAILABLE
# ② wallet 다운로드
oci db autonomous-database generate-wallet --autonomous-database-id <adb_ocid> --file <path>/wallet.zip --password ***MASKED***
```

- **실행 명령 로깅**: 이 엔드포인트는 DB SQL을 실행하지 않으므로, envelope의 `executed_sql[]`에 SQL 대신 **실행된 OCI CLI 명령 원문**을 담는다 (SqlLogTerminal에 동일하게 누적 표시). `--password` 값은 `***MASKED***` 치환 (§1.5 규칙 2 적용).
- **비동기 처리/타임아웃**: 다운로드는 수십 초가 걸릴 수 있다. subprocess는 `asyncio.create_subprocess_exec`로 비차단 실행하며, 단계별 타임아웃은 ① 조회 30초 / ② 다운로드 120초 — 초과 시 `504 OCI_CLI_TIMEOUT`. 프론트는 진행 상태(조회중 → 다운로드중 → 해제중)를 표시한다 (design.md PG-01).
- **응답 200**: §2.1 업로드와 동일 스키마(`wallet_id` + alias 목록) + `adb_ocid`:

```json
{
  "data": {
    "wallet_id": "wlt_7c1e4b",
    "tns_aliases": ["demoadb_high", "demoadb_medium", "demoadb_low", "demoadb_tp", "demoadb_tpurgent"],
    "files_found": ["tnsnames.ora", "sqlnet.ora", "ewallet.pem"],
    "adb_ocid": "ocid1.autonomousdatabase.oc1..xxxx"
  },
  "executed_sql": [
    "oci db autonomous-database list --compartment-id ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq --display-name DEMOADB --lifecycle-state AVAILABLE",
    "oci db autonomous-database generate-wallet --autonomous-database-id ocid1.autonomousdatabase.oc1..xxxx --file ~/.selectai/wallets/wlt_7c1e4b/wallet.zip --password ***MASKED***"
  ],
  "elapsed_ms": 23400
}
```

- **오류**:
  - `409 ADB_AMBIGUOUS` — 동일 표시 이름의 ADB가 복수 매칭. `error.detail` 대신 `error` 객체에 후보 목록을 동봉해 사용자가 선택 후 `adb_ocid`로 재호출:

```json
{
  "error": {
    "code": "ADB_AMBIGUOUS", "app_code": "ADB_AMBIGUOUS",
    "message_ko": "같은 이름의 ADB가 여러 개 발견되었습니다. 목록에서 하나를 선택하세요.",
    "hint_ko": "선택한 항목의 adb_ocid를 지정해 다시 요청하세요.",
    "retryable": true,
    "candidates": [
      { "adb_ocid": "ocid1.autonomousdatabase.oc1..xxxx", "display_name": "DEMOADB", "workload_type": "DW" },
      { "adb_ocid": "ocid1.autonomousdatabase.oc1..yyyy", "display_name": "DEMOADB", "workload_type": "OLTP" }
    ]
  }
}
```

  - `404 ADB_NOT_FOUND` — 매칭 0건 ("해당 이름의 AVAILABLE 상태 ADB를 찾을 수 없습니다. 컴파트먼트와 표시 이름을 확인하세요").
  - `424 OCI_CLI_NOT_FOUND` — CLI 미설치 ("OCI CLI가 설치되어 있지 않습니다. 수동 업로드를 이용하거나 설치 가이드를 참조하세요" + `hint_ko`로 업로드 경로 폴백 유도).
  - `401 OCI_CLI_AUTH_FAILED` — `~/.oci/config` 인증 실패 (업로드 폴백 유도).
  - `504 OCI_CLI_TIMEOUT` — 단계 타임아웃 초과 (`retryable: true`).

---

## 3. Privileges — 권한 사전 점검/원클릭 적용 (FR-03)

### 3.1 `GET /api/v1/privileges/check` — 점검

- **쿼리 파라미터**:
  - `provider` (기본 `oci`) — ACL 분기 판단 (레퍼런스 §4.2 p34: **OCI GenAI는 ACL 불필요**)
  - `target_user` (기본 `ADMIN`) — grant 시연 대상 사용자
  - `include` (옵션, CSV) — `feedback`(P1), `rag`(P2) 항목 포함 여부
- **점검 항목과 내부 SQL** (레퍼런스 §4):

| check_id | 점검 내용 | 내부 SQL |
|---|---|---|
| `execute_dbms_cloud_ai` | `DBMS_CLOUD_AI` EXECUTE 보유 | `SELECT table_name, privilege FROM DBA_TAB_PRIVS WHERE grantee = :user AND table_name = 'DBMS_CLOUD_AI'` (p35) |
| `execute_dbms_cloud_pipeline` | RAG용 (P2, `include=rag` 시) | 동일 쿼리 `table_name = 'DBMS_CLOUD_PIPELINE'` |
| `credential` | AI 공급자 자격증명 존재 | `SELECT credential_name, enabled FROM DBA_CREDENTIALS WHERE owner = :user` |
| `resource_principal` | `OCI$RESOURCE_PRINCIPAL` 사용 가능 | `SELECT credential_name FROM DBA_CREDENTIALS WHERE credential_name = 'OCI$RESOURCE_PRINCIPAL'` |
| `network_acl` | 외부 공급자 host ACL (**provider=oci면 `not_applicable`**) | `SELECT host, lower_port, upper_port, ace_order FROM DBA_HOST_ACES WHERE principal = :user AND host = :provider_host` |
| `data_access` | Data Access 활성 여부 (ORA-20000 예방, R2) | narrate 가능 여부 프로브: `GENERATE(action=>'narrate')`를 시스템 고정 프롬프트로 dry-run 하거나, 직전 ENABLE/DISABLE 적용 이력을 앱 DB에 기록·표시. 미확정 시 상태 `unknown`으로 표시하고 ENABLE 원클릭 제공 |
| `feedback_grants` | P1, `include=feedback` 시: `SYS.V_$MAPPED_SQL` / `SYS.V_$SESSION` READ (p64) | `SELECT table_name FROM DBA_TAB_PRIVS WHERE grantee = :user AND privilege = 'READ' AND table_name IN ('V_$MAPPED_SQL','V_$SESSION')` |

- **응답 200**:

```json
{
  "data": {
    "provider": "oci",
    "target_user": "ADMIN",
    "overall": "action_required",
    "checks": [
      {
        "check_id": "execute_dbms_cloud_ai",
        "title_ko": "DBMS_CLOUD_AI 실행 권한",
        "status": "pass",
        "description_ko": "Select AI의 모든 기능은 DBMS_CLOUD_AI 패키지 EXECUTE 권한이 필요합니다.",
        "evidence_sql": "SELECT table_name, privilege FROM DBA_TAB_PRIVS WHERE ...",
        "fix_sql": null,
        "docs_ref": "selectai-reference.md §4.1 (p33-35)"
      },
      {
        "check_id": "network_acl",
        "title_ko": "네트워크 ACL",
        "status": "not_applicable",
        "description_ko": "OCI Generative AI는 네트워크 ACL이 필요 없습니다 (p34). 외부 공급자 선택 시에만 점검합니다.",
        "evidence_sql": null, "fix_sql": null,
        "docs_ref": "selectai-reference.md §4.2 (p34)"
      },
      {
        "check_id": "resource_principal",
        "title_ko": "Resource Principal 인증",
        "status": "fail",
        "description_ko": "자격증명 키 없이 OCI GenAI를 호출하려면 Resource Principal을 활성화해야 합니다.",
        "evidence_sql": "SELECT credential_name FROM DBA_CREDENTIALS WHERE ...",
        "fix_sql": "BEGIN\n  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI');\nEND;",
        "docs_ref": "selectai-reference.md §4.4 (p81)"
      }
    ]
  },
  "executed_sql": ["SELECT table_name, privilege FROM DBA_TAB_PRIVS WHERE ..."],
  "elapsed_ms": 950
}
```

- `status` enum: `pass` | `fail` | `not_applicable` | `unknown`
- `fix_sql`은 "적용 전 SQL 미리보기" 수용 기준을 위해 점검 응답에 **항상 포함**.

### 3.2 `POST /api/v1/privileges/apply` — 원클릭 적용

- **요청**:

```json
{
  "provider": "oci",
  "target_user": "ADMIN",
  "items": [
    { "check_id": "resource_principal" },
    { "check_id": "execute_dbms_cloud_ai" },
    { "check_id": "credential",
      "credential": { "credential_name": "GENAI_CRED", "auth_type": "api_key",
                      "user_ocid": "ocid1.user.oc1..aaa", "tenancy_ocid": "ocid1.tenancy.oc1..aaa",
                      "private_key": "-----BEGIN PRIVATE KEY-----...", "fingerprint": "aa:bb:..." } },
    { "check_id": "data_access", "enable": true }
  ],
  "recheck": true
}
```

- **항목별 내부 PL/SQL** (레퍼런스 §4 원문 그대로):

```sql
-- execute_dbms_cloud_ai
GRANT EXECUTE ON DBMS_CLOUD_AI TO ADMIN;

-- execute_dbms_cloud_pipeline (P2)
GRANT EXECUTE ON DBMS_CLOUD_PIPELINE TO ADMIN;

-- resource_principal (프로시저명 주의: ENABLE_RESOURCE_PRINCIPAL 아님)
BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI');
END;
/

-- credential (auth_type=api_key, OCI API 서명 키)
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => :credential_name,
    user_ocid       => :user_ocid,
    tenancy_ocid    => :tenancy_ocid,
    private_key     => :private_key,
    fingerprint     => :fingerprint);
END;
/

-- credential (auth_type=api_token, 외부 공급자)
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => :credential_name,
    username        => :username,
    password        => :api_token);
END;
/

-- network_acl (외부 공급자 선택 시에만 실행, provider=oci면 400 ACL_NOT_REQUIRED)
BEGIN
  DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
    host => :provider_host,   -- openai: api.openai.com, cohere: api.cohere.ai 등 (p36)
    ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                        principal_name => :target_user,
                        principal_type => xs_acl.ptype_db));
END;
/

-- data_access (enable 플래그에 따라 둘 중 하나만 실행)
BEGIN DBMS_CLOUD_AI.ENABLE_DATA_ACCESS; END;   -- enable=true
/
BEGIN DBMS_CLOUD_AI.DISABLE_DATA_ACCESS; END;  -- enable=false (거버넌스 시연 P1)
/

-- feedback_grants (P1)
GRANT READ ON SYS.V_$MAPPED_SQL TO ADMIN;
GRANT READ ON SYS.V_$SESSION TO ADMIN;
```

- **응답 200**: 항목별 적용 결과 + `recheck=true`면 재점검 결과 동봉 (FR-03 "적용 후 자동 재점검"):

```json
{
  "data": {
    "applied": [
      { "check_id": "resource_principal", "ok": true,
        "executed_sql": "BEGIN\n  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI');\nEND;" },
      { "check_id": "credential", "ok": true,
        "executed_sql": "BEGIN\n  DBMS_CLOUD.CREATE_CREDENTIAL(credential_name => 'GENAI_CRED', user_ocid => '***MASKED***', ...);\nEND;" }
    ],
    "recheck": { "overall": "pass", "checks": [ "...§3.1과 동일 스키마..." ] }
  },
  "executed_sql": ["..."],
  "elapsed_ms": 3300
}
```

- **오류**: `403 INSUFFICIENT_PRIVILEGE` (ADMIN 아님), `400 ACL_NOT_REQUIRED` (provider=oci에서 network_acl 요청), `409 PARTIAL_APPLY` (일부 실패 — `applied[].ok=false` + 항목별 오류 동봉).

---

## 4. Profiles — 프로파일 설정/관리 (FR-04, FR-05)

### 4.1 `GET /api/v1/profiles/attribute-meta` — 속성 스키마/한국어 해설 메타데이터

DB 미접속으로 동작하는 정적 메타데이터. **레퍼런스 §3에서 검증된 21개 속성만** 폼 스키마로 제공하고(R4), 그 외 속성은 클라이언트의 "고급 JSON 직접 입력"으로 격리한다.

- **응답 200** (발췌):

```json
{
  "data": {
    "verified_attributes": [
      {
        "name": "provider",
        "type": "enum",
        "enum": ["oci", "openai", "azure", "google", "cohere", "anthropic", "aws"],
        "default": "oci",
        "required": true,
        "description_ko": "AI 공급자. OpenAI 호환 공급자는 provider 대신 provider_endpoint로 지정합니다.",
        "docs_ref": "p17, p78",
        "ui_group": "provider"
      },
      {
        "name": "comments",
        "type": "boolean_string",
        "default": "false",
        "description_ko": "\"true\"면 테이블/컬럼 COMMENT를 LLM 메타데이터에 포함하여 SQL 생성 정확도를 높입니다. 메타데이터 증강 전/후 비교 데모의 핵심 속성입니다.",
        "docs_ref": "p147-149",
        "ui_group": "metadata"
      },
      {
        "name": "model",
        "type": "enum_or_text",
        "default": "meta.llama-3.3-70b-instruct",
        "enum": ["meta.llama-3.3-70b-instruct", "meta.llama-3.2-90b-vision-instruct",
                 "meta.llama-3.2-11b-vision-instruct", "meta.llama-3.1-70b-instruct",
                 "meta.llama-3.1-405b-instruct", "cohere.command-r-08-2024",
                 "cohere.command-r-plus-08-2024", "cohere.command-r-16k",
                 "cohere.command-r-plus", "xai.grok-3", "xai.grok-3-fast",
                 "xai.grok-3-mini", "xai.grok-3-mini-fast", "xai.grok-4",
                 "xai.grok-4-fast-reasoning", "xai.grok-4-fast-non-reasoning"],
        "deprecated": ["cohere.command-r-16k", "cohere.command-r-plus"],
        "description_ko": "LLM 모델명. 모델 OCID 지정 시 oci_apiformat이 필요합니다. `deprecated` 목록의 모델은 UI에서 비활성/경고 배지로 표기하되 전송 값은 순수 모델명을 사용합니다.",
        "docs_ref": "p15, p84, p91-92",
        "ui_group": "provider"
      }
    ],
    "defaults": {
      "provider": "oci",
      "credential_name": "OCI$RESOURCE_PRINCIPAL",
      "model": "meta.llama-3.3-70b-instruct",
      "region": "us-chicago-1",
      "oci_compartment_id": "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq"
    }
  },
  "executed_sql": [],
  "elapsed_ms": 2
}
```

- `verified_attributes`에는 21개 전부 포함: `provider`, `credential_name`, `object_list`, `object_list_mode`, `comments`, `annotations`, `constraints`, `conversation`, `temperature`, `max_tokens`, `model`, `region`, `oci_compartment_id`, `oci_apiformat`, `oci_endpoint_id`, `enforce_object_list`, `case_sensitive_values`, `target_language`, `vector_index_name`, `azure_resource_name`/`azure_deployment_name`, `provider_endpoint`. 각 항목의 `description_ko`는 레퍼런스 §3 해설 문구를 사용한다 (G4: 커버리지 100%).

### 4.2 `POST /api/v1/profiles/preview` — CREATE_PROFILE SQL 미리보기 (실행 안 함)

- **요청** (4.3과 동일 본문 + 실행 없음):

```json
{
  "profile_name": "GENAI_DEMO",
  "attributes": {
    "provider": "oci",
    "credential_name": "OCI$RESOURCE_PRINCIPAL",
    "object_list": [{ "owner": "SH", "name": "customers" }, { "owner": "SH", "name": "countries" }],
    "model": "meta.llama-3.3-70b-instruct",
    "region": "us-chicago-1",
    "oci_compartment_id": "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq",
    "comments": "true"
  },
  "extra_attributes_json": null
}
```

- **응답 200**:

```json
{
  "data": {
    "sql_preview": "BEGIN\n  DBMS_CLOUD_AI.CREATE_PROFILE(\n      profile_name => 'GENAI_DEMO',\n      attributes   => '{\"provider\": \"oci\", ...}');\nEND;",
    "warnings_ko": ["외부 공급자(openai)를 선택하면 네트워크 ACL이 필요합니다. 권한 점검을 먼저 실행하세요."]
  },
  "executed_sql": [],
  "elapsed_ms": 4
}
```

- `extra_attributes_json`: 미검증 속성용 "고급 JSON" 문자열. 검증 21개와 키 충돌 시 `400 ATTRIBUTE_CONFLICT`.
- 외부 공급자 + ACL 미점검이면 `warnings_ko`에 FR-03 연동 경고 (FR-04 수용 기준).

### 4.3 `POST /api/v1/profiles` — 프로파일 생성

- **요청**: 4.2와 동일.
- **내부 PL/SQL** (레퍼런스 §5 p84-85):

```sql
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => :profile_name,
      attributes   => :attributes_json);
END;
/
```

- **응답 201**: `{ "data": { "profile_name": "GENAI_DEMO", "status": "ENABLED", "attributes": {...} }, "executed_sql": ["BEGIN\n  DBMS_CLOUD_AI.CREATE_PROFILE(...);\nEND;"], "elapsed_ms": 870 }`
- **오류**: `409 PROFILE_EXISTS`, `400 ATTRIBUTE_INVALID` (JSON 파싱/타입 오류), `403 INSUFFICIENT_PRIVILEGE`.

### 4.4 `GET /api/v1/profiles` — 목록

- **내부 SQL** (레퍼런스 §2 뷰, p256):

```sql
SELECT profile_name, status FROM USER_CLOUD_AI_PROFILES ORDER BY profile_name;
```

- **응답**: 각 프로파일에 `provider`/`model` 요약을 붙이기 위해 속성 뷰를 조인 조회:

```sql
SELECT profile_name, attribute_name, attribute_value
  FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES
 WHERE attribute_name IN ('provider', 'model');
```

```json
{ "data": [ { "profile_name": "GENAI_DEMO", "status": "ENABLED",
              "provider": "oci", "model": "meta.llama-3.3-70b-instruct",
              "is_default": true } ],
  "executed_sql": ["SELECT profile_name, status FROM USER_CLOUD_AI_PROFILES ..."], "elapsed_ms": 60 }
```

- `is_default`는 DB가 아닌 **앱 설정**(§4.8)에서 합성한다.

### 4.5 `GET /api/v1/profiles/{profile_name}` — 속성 상세 ("showparameter" 대체)

- **내부 SQL**:

```sql
SELECT attribute_name, attribute_value
  FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES
 WHERE profile_name = :profile_name;
```

- **응답 200**: 속성 값 + §4.1 메타데이터의 `description_ko`를 병합해 반환 (FR-05 수용 기준 — 한국어 해설과 함께 표시):

```json
{
  "data": {
    "profile_name": "GENAI_DEMO",
    "status": "ENABLED",
    "attributes": [
      { "name": "comments", "value": "true", "verified": true,
        "description_ko": "테이블/컬럼 COMMENT를 LLM 메타데이터에 포함...", "docs_ref": "p147-149" },
      { "name": "some_unverified_attr", "value": "x", "verified": false,
        "description_ko": "본 가이드에서 미검증 속성입니다. Supplied Package Reference를 확인하세요.", "docs_ref": null }
    ]
  },
  "executed_sql": ["SELECT attribute_name, attribute_value FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES ..."],
  "elapsed_ms": 45
}
```

### 4.6 `PATCH /api/v1/profiles/{profile_name}` — 속성 수정

- **요청**: `{ "attributes": { "temperature": "0.2", "comments": "true" }, "preview_only": false }`
- **내부 PL/SQL**: 단일 속성이면 `SET_ATTRIBUTE`, 복수면 `SET_ATTRIBUTES` (레퍼런스 §2):

```sql
BEGIN
  DBMS_CLOUD_AI.SET_ATTRIBUTES(
      profile_name => :profile_name,
      attributes   => :attributes_json);
END;
/
```

- `preview_only=true`면 실행 없이 `sql_preview`만 반환 (FR-05 수용 기준 — 수정 SQL 미리보기).
- **응답 200**: 수정 후 §4.5와 동일 상세 + `executed_sql`.

### 4.7 `DELETE /api/v1/profiles/{profile_name}` — 삭제

```sql
BEGIN DBMS_CLOUD_AI.DROP_PROFILE(:profile_name); END;
```

- 삭제 대상이 앱 기본 프로파일이면 기본 설정도 해제하고 응답에 `default_cleared: true` 포함.
- **응답 204**(본문 없음) 대신 **200** + `{ "data": { "dropped": true, "default_cleared": true } }` — 기본 해제 통지 필요.

### 4.8 기본 프로파일 (앱 설정 — DB 미사용)

> 설계 결정(PRD FR-05): `SET_PROFILE`은 세션 상태이므로 사용하지 않는다. 기본 프로파일은 **커넥션별 앱 설정**으로 저장하고, 모든 GENERATE 호출에 `profile_name`을 명시 전달한다.

- `GET /api/v1/settings/default-profile` → `{ "data": { "profile_name": "GENAI_DEMO" } }`
- `PUT /api/v1/settings/default-profile` — 요청 `{ "profile_name": "GENAI_DEMO" }`. 존재·ENABLED 검증 후 저장. 오류: `404 PROFILE_NOT_FOUND`, `409 PROFILE_DISABLED`.

### 4.9 `POST /api/v1/profiles/{profile_name}/status` — ENABLE/DISABLE 토글 (P1)

- **요청**: `{ "enabled": false }`
- **내부 PL/SQL**: `BEGIN DBMS_CLOUD_AI.DISABLE_PROFILE(:profile_name); END;` / `ENABLE_PROFILE`.

---

## 5. Select AI — 액션 실행 (FR-06)

### 5.1 `GET /api/v1/selectai/actions` — 액션 메타데이터

정적 응답. **액션 목록은 레퍼런스 §1 ch8 공식 표만** 사용. `showparameter`는 존재하지 않으므로 미포함. `agent`는 범위 외로 미포함.

```json
{
  "data": [
    { "action": "runsql",     "priority": "P0", "title_ko": "SQL 생성+실행", "result_type": "table",
      "description_ko": "자연어로 SQL을 생성하고 즉시 실행해 결과를 표로 반환합니다 (기본 액션)." },
    { "action": "showsql",    "priority": "P0", "title_ko": "SQL만 표시",    "result_type": "sql",
      "description_ko": "생성된 SQL 문장만 표시하고 실행하지 않습니다." },
    { "action": "explainsql", "priority": "P0", "title_ko": "SQL+설명",     "result_type": "text",
      "description_ko": "생성된 SQL과 LLM의 자연어 설명을 함께 반환합니다." },
    { "action": "narrate",    "priority": "P0", "title_ko": "결과 서술",     "result_type": "text",
      "description_ko": "SQL 실행 결과를 자연어로 서술합니다. Data Access 비활성 시 ORA-20000으로 실패합니다." },
    { "action": "chat",       "priority": "P0", "title_ko": "LLM 대화",     "result_type": "text",
      "description_ko": "프롬프트를 LLM에 직접 전달합니다 (pass-through)." },
    { "action": "showprompt", "priority": "P1", "title_ko": "증강 프롬프트 보기", "result_type": "text",
      "description_ko": "LLM에 전송되는 증강 프롬프트 원문을 표시합니다 (NL2SQL·RAG 지원)." },
    { "action": "feedback",   "priority": "P1", "title_ko": "피드백",        "result_type": "text",
      "description_ko": "생성 SQL에 긍정/부정 피드백을 제공해 이후 정확도를 개선합니다 (26ai 전용)." },
    { "action": "summarize",  "priority": "P2", "title_ko": "요약",         "result_type": "text" },
    { "action": "translate",  "priority": "P2", "title_ko": "번역",         "result_type": "text",
      "description_ko": "provider가 oci일 때만 지원, target_language 속성 필요." }
  ],
  "executed_sql": [], "elapsed_ms": 1
}
```

### 5.2 `POST /api/v1/selectai/generate` — 액션 실행 (핵심 엔드포인트)

- **요청**:

```json
{
  "prompt": "how many customers in San Francisco are married",
  "action": "runsql",
  "profile_name": null,
  "conversation_id": null,
  "row_limit": 100
}
```

- `profile_name` null이면 앱 기본 프로파일(§4.8) 사용. 기본도 없으면 `400 NO_PROFILE`.
- `conversation_id`는 챗봇 외 화면에서도 옵션 허용 (맥락 비교 시연 재사용).
- **내부 SQL — 표준 패턴** (레퍼런스 §2 p129):

```sql
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => :prompt,
         profile_name => :profile_name,
         action       => :action,
         params       => :params_json   -- conversation_id 있을 때만: '{"conversation_id":"<uuid>"}'
       ) AS response
  FROM dual;
```

- **`runsql`의 구조화 결과 처리(구현 노트)**: `GENERATE(action=>'runsql')`의 반환은 CLOB 텍스트다. 표(grid) 렌더링을 위해 백엔드는 2단계로 실행한다 — ① `GENERATE(action=>'showsql')`로 SQL 획득 → ② 획득한 SELECT 문을 직접 실행해 컬럼/행을 JSON으로 반환(`row_limit` 적용, SELECT 외 문장이면 `422 GENERATED_SQL_INVALID`로 차단). 두 단계 모두 `executed_sql`에 노출한다.
- **응답 200 (runsql)**:

```json
{
  "data": {
    "action": "runsql",
    "profile_name": "GENAI_DEMO",
    "result_type": "table",
    "generated_sql": "SELECT COUNT(*) FROM SH.CUSTOMERS c JOIN ... WHERE c.CUST_CITY = 'San Francisco' AND c.CUST_MARITAL_STATUS = 'married'",
    "columns": ["COUNT(*)"],
    "rows": [[18]],
    "row_count": 1,
    "truncated": false,
    "response_text": null
  },
  "executed_sql": [
    "SELECT DBMS_CLOUD_AI.GENERATE(prompt => :1, profile_name => :2, action => 'showsql') FROM dual",
    "SELECT COUNT(*) FROM SH.CUSTOMERS c JOIN ... -- row_limit 100"
  ],
  "elapsed_ms": 6240
}
```

- **응답 200 (showsql/explainsql/narrate/chat/showprompt)**: `result_type`이 `sql`/`text`, `response_text`에 GENERATE 반환 CLOB 전문, `generated_sql`은 showsql/explainsql일 때 파싱 가능하면 채움.
- **오류**: `409 DATA_ACCESS_DISABLED` (narrate), `422 GENERATED_SQL_INVALID` / `404 OBJECT_NOT_FOUND` (LLM 환각 — `retryable: true`), `504 LLM_TIMEOUT`, `404 PROFILE_NOT_FOUND`.

### 5.3 `POST /api/v1/selectai/feedback` — 피드백 (P1)

- **요청**:

```json
{
  "profile_name": "GENAI_DEMO",
  "sql_text": "how many customers in San Francisco are married",
  "feedback_type": "negative",
  "response": "SELECT COUNT(*) FROM SH.CUSTOMERS WHERE ...",
  "feedback_content": "married 상태 비교에 UPPER를 사용해 주세요",
  "operation": "add"
}
```

- **내부 PL/SQL** (레퍼런스 §2 FEEDBACK):

```sql
BEGIN
  DBMS_CLOUD_AI.FEEDBACK(
      profile_name     => :profile_name,
      sql_text         => :sql_text,          -- 또는 sql_id (V$MAPPED_SQL 조회)
      feedback_type    => :feedback_type,     -- 'positive' | 'negative'
      response         => :response,          -- negative 시 올바른 SQL
      feedback_content => :feedback_content,
      operation        => :operation);        -- 'add' | 'delete'
END;
/
```

- **사전 조건**: `feedback_grants` 점검 통과 (§3.1, p64). 미통과면 `403 INSUFFICIENT_PRIVILEGE` + `hint_ko`로 권한 화면 유도. RAG 프로파일이면 `400 FEEDBACK_NOT_SUPPORTED`.

### 5.4 `GET /api/v1/selectai/suggested-prompts` — 추천 프롬프트 (canned)

정적. SH 스키마 검증 예제(레퍼런스 §9) 기반: `how many customers exist`, `how many customers in San Francisco are married`, `what are the top 3 customers in San Francisco` 등. 응답: `{ "data": [ { "prompt": "...", "recommended_action": "runsql", "schema": "SH" } ] }`

---

## 6. Chat — Conversations 챗봇 (FR-07)

### 6.1 `POST /api/v1/chat/conversations` — 대화 생성

- **요청** (기본값 제공 — retention 기본값은 오픈 이슈 O4, 잠정 7일):

```json
{ "title": "Demo chat", "description": "Select AI demo conversation",
  "retention_days": 7, "conversation_length": 10 }
```

- **내부 SQL** (레퍼런스 §6 — Function형 CREATE_CONVERSATION, 세션 설정 Procedure형 사용 금지):

```sql
SELECT DBMS_CLOUD_AI.CREATE_CONVERSATION(
         attributes => '{"title":"Demo chat","description":"Select AI demo conversation","retention_days":7,"conversation_length":10}'
       ) AS conversation_id
  FROM dual;
```

- **응답 201**: `{ "data": { "conversation_id": "30C9DB6E-EA4D-AFBA-E063-9C6D46644B92", "title": "Demo chat", ... }, "executed_sql": [...], "elapsed_ms": 300 }`

### 6.2 `POST /api/v1/chat/conversations/{conversation_id}/messages` — 메시지 전송(턴)

- **요청**:

```json
{ "prompt": "break out count of customers by country", "action": "narrate", "profile_name": null }
```

- `action`은 대화 지원 5종만 허용: `runsql`, `showsql`, `explainsql`, `narrate`, `chat` (p47 Note). 그 외 `400 ACTION_NOT_SUPPORTED_IN_CONVERSATION`. 기본값 `narrate`.
- **내부 SQL — conversation_id를 params로 전달 (SET_CONVERSATION_ID 미사용)**:

```sql
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => :prompt,
         profile_name => :profile_name,
         action       => :action,
        params       => :params_json
       ) AS response
  FROM dual;
```

`params_json`은 백엔드가 `json.dumps({"conversation_id": conversation_id})`로 직렬화한 전체 JSON 문자열을 단일 바인드로 전달한다. SQL 문자열 연결로 JSON을 조립하지 않는다.

- **응답 200**: §5.2와 동일 결과 스키마 + `conversation_id` 에코. runsql이면 table 구조화 동일 적용.

### 6.3 `GET /api/v1/chat/conversations` — 대화 목록

```sql
SELECT conversation_id, conversation_title, description, retention_days, conversation_length
  FROM USER_CLOUD_AI_CONVERSATIONS;
```

### 6.4 `GET /api/v1/chat/conversations/{conversation_id}/messages` — 턴 이력

```sql
SELECT * FROM USER_CLOUD_AI_CONVERSATION_PROMPTS WHERE conversation_id = :conversation_id;
```

- **응답**: `{ "data": { "conversation_id": "...", "messages": [ { "prompt_id": "...", "prompt": "...", "response": "...", "action": "narrate", "created_at": "..." } ] } }`

### 6.5 `PATCH /api/v1/chat/conversations/{conversation_id}` — 속성 수정

```sql
BEGIN
  DBMS_CLOUD_AI.UPDATE_CONVERSATION(:conversation_id,
      attributes => '{"title":"a title","retention_days":20}');
END;
```

### 6.6 `DELETE /api/v1/chat/conversations/{conversation_id}` — 대화 종료/삭제

```sql
BEGIN DBMS_CLOUD_AI.DROP_CONVERSATION(:conversation_id); END;
```

- 개별 턴 삭제(보조): `DELETE /api/v1/chat/conversations/{conversation_id}/messages/{prompt_id}` → `DBMS_CLOUD_AI.DELETE_CONVERSATION_PROMPT(:prompt_id)`.

### 6.7 `POST /api/v1/chat/compare` — 맥락 유무 비교 모드 (FR-07 수용 기준, p132 근거)

동일 프롬프트를 conversation_id **없이/있이** 병렬 실행해 응답 차이를 반환한다.

- **요청**: `{ "prompt": "break out count of customers by country", "action": "chat", "conversation_id": "30C9DB6E-...", "profile_name": null }`
- **내부 SQL**: GENERATE 2회 — ① `params` 없이, ② `params => :params_json`. 두 호출은 병렬 실행한다.
- **응답 200**:

```json
{
  "data": {
    "without_context": { "response_text": "...(이전 질문 맥락 없음 — 모호한 답변)..." },
    "with_context":    { "response_text": "...(직전 'total customers' 맥락 반영 답변)..." }
  },
  "executed_sql": ["SELECT DBMS_CLOUD_AI.GENERATE(... action => 'chat') FROM dual",
                    "SELECT DBMS_CLOUD_AI.GENERATE(... params => '{\"conversation_id\":\"...\"}') FROM dual"],
  "elapsed_ms": 9100
}
```

---

## 7. Enrichment — Comment/Annotation 증강 전/후 비교 (FR-08)

### 7.1 `POST /api/v1/enrichment/demo-schema` — 모호 스키마 원클릭 생성/초기화

레퍼런스 §9 무비 테이블 패턴(의도적으로 모호한 컬럼명 c1~c7)을 생성하고 샘플 데이터를 시드한다. 백엔드는 `backend/seeds/movie_schema.sql`을 실행한다.

- **요청**: `{ "reset": true }` — `reset=true`면 DROP 후 재생성.
- **내부 SQL(요지)**:

```sql
CREATE TABLE table1 (c1 NUMBER, c2 VARCHAR2(200), c3 NUMBER);          -- movies
CREATE TABLE table2 (c1 NUMBER, c6 DATE, c7 NUMBER);                   -- watch history (c7 = views)
CREATE TABLE table3 (c1 NUMBER, c4 VARCHAR2(100), c5 VARCHAR2(100));   -- devices/users
INSERT INTO table1 VALUES (...); -- 시드 데이터
```

- **응답 201**: `{ "data": { "tables": ["TABLE1","TABLE2","TABLE3"], "seeded_rows": 120 }, "executed_sql": ["CREATE TABLE table1 ..."], "elapsed_ms": 2100 }`
- `DELETE /api/v1/enrichment/demo-schema` — `backend/seeds/movie_reset.sql`을 기준으로 데모 테이블/비교용 프로파일 쌍을 정리한다. 앱 전체 정리는 §10 Cleanup API를 사용한다.

### 7.2 `GET /api/v1/enrichment/comments` — 코멘트 조회

- **쿼리**: `?owner=ADMIN&table=TABLE1` (table 생략 시 owner 전체)
- **내부 SQL**:

```sql
SELECT table_name, comments FROM ALL_TAB_COMMENTS WHERE owner = :owner AND table_name = :table;
SELECT table_name, column_name, comments FROM ALL_COL_COMMENTS WHERE owner = :owner AND table_name = :table;
```

- **응답**: 테이블 코멘트 + 컬럼별 코멘트 목록(컬럼 타입 포함 — schema 리소스 조인).

### 7.3 `PUT /api/v1/enrichment/comments` — 코멘트 작성/적용 (DDL 미리보기 지원)

- **요청**:

```json
{
  "owner": "ADMIN",
  "table_comment": { "table": "TABLE1", "comment": "Contains movies, movie titles and the year it was released" },
  "column_comments": [
    { "table": "TABLE1", "column": "C1", "comment": "movie ids. Use this column to join to other tables" },
    { "table": "TABLE1", "column": "C2", "comment": "movie titles" },
    { "table": "TABLE2", "column": "C7", "comment": "number of views, watched, streamed" }
  ],
  "preview_only": false
}
```

- **내부 DDL** (레퍼런스 §7 p147-149 원문 패턴 — 코멘트 내 작은따옴표는 `''` 이스케이프):

```sql
COMMENT ON TABLE table1 IS 'Contains movies, movie titles and the year it was released';
COMMENT ON COLUMN table1.c1 IS 'movie ids. Use this column to join to other tables';
COMMENT ON COLUMN table2.c7 IS 'number of views, watched, streamed';
```

- `preview_only=true`면 실행 없이 `sql_preview` 배열만 반환 (FR-08 수용 기준 — DDL 미리보기).
- **응답 200**: 적용된 DDL 목록 + 적용 후 §7.2 재조회 결과.

### 7.4 `POST /api/v1/enrichment/profile-pair` — 전/후 프로파일 쌍 자동 생성

`comments:"false"` / `comments:"true"`만 다른 두 프로파일을 만든다 (FR-08 ②④단계).

- **요청**:

```json
{
  "base_name": "ENRICH_DEMO",
  "object_list": [ { "owner": "ADMIN", "name": "TABLE1" }, { "owner": "ADMIN", "name": "TABLE2" }, { "owner": "ADMIN", "name": "TABLE3" } ],
  "annotations": false,
  "constraints": false
}
```

- **내부 PL/SQL**: `DBMS_CLOUD_AI.CREATE_PROFILE` 2회 — `ENRICH_DEMO_OFF`(`"comments":"false"`), `ENRICH_DEMO_ON`(`"comments":"true"`). 나머지 속성은 기본값(§4.1 defaults). 이미 존재하면 `DROP_PROFILE` 후 재생성.
- **응답 201**: `{ "data": { "profile_off": "ENRICH_DEMO_OFF", "profile_on": "ENRICH_DEMO_ON" }, ... }`
- (P1) `annotations`/`constraints` true 시 ON 프로파일에 `"annotations":"true"`/`"constraints":"true"` 추가 (p149-150).

### 7.5 `POST /api/v1/enrichment/compare` — 전/후 비교 실행 (좌우 분할 데이터)

- **요청**:

```json
{ "prompt": "what are our total views",
  "profile_off": "ENRICH_DEMO_OFF", "profile_on": "ENRICH_DEMO_ON",
  "action": "showsql", "include_showprompt": false }
```

- `action`: `showsql`(기본 — SQL 비교) 또는 `runsql`(결과까지 비교).
- **내부 SQL**: 동일 prompt로 `GENERATE`를 프로파일만 바꿔 2회(병렬) 실행. `include_showprompt=true`(P1)면 ON 프로파일에 `action=>'showprompt'` 1회 추가 — 증강 프롬프트에 COMMENT 포함 확인용.
- **응답 200**:

```json
{
  "data": {
    "prompt": "what are our total views",
    "before": { "profile_name": "ENRICH_DEMO_OFF",
                "generated_sql": "SELECT SUM(QUANTITY_SOLD) FROM ...  -- 잘못된 컬럼 선택",
                "columns": null, "rows": null, "error": null },
    "after":  { "profile_name": "ENRICH_DEMO_ON",
                "generated_sql": "SELECT SUM(t2.c7) FROM table2 t2  -- COMMENT 기반 정확한 매핑",
                "columns": null, "rows": null, "error": null },
    "augmented_prompt": null
  },
  "executed_sql": ["SELECT DBMS_CLOUD_AI.GENERATE(... profile_name => 'ENRICH_DEMO_OFF' ...) FROM dual",
                    "SELECT DBMS_CLOUD_AI.GENERATE(... profile_name => 'ENRICH_DEMO_ON' ...) FROM dual"],
  "elapsed_ms": 11300
}
```

- 한쪽 실행이 LLM 환각으로 실패해도 전체를 실패시키지 않고 해당 측 `error` 필드에 §1.4 오류 객체를 담는다 (전/후 "오답 vs 정답" 시연 자체가 목적).

---

## 8. Schema — 테이블/컬럼 브라우징 (FR-04 object_list 선택, FR-08 지원)

이 절의 모든 조회는 **인증한 커넥션 사용자(admin)가 접근 가능한 객체만** 반환한다 — `ALL_*` 데이터 딕셔너리 뷰를 사용하므로 "DB에 보이는 것"과 정확히 일치한다. 프로파일 생성 화면(PG-03a)은 이 엔드포인트로 스키마/테이블을 브라우징하고, 사용자가 체크한 테이블이 그대로 `object_list`로 들어가 `CREATE_PROFILE`이 호출된다 (FR-04).

### 8.1 `GET /api/v1/schema/owners`

접근 가능한 스키마(소유자) 목록을 반환하되, 인증한 사용자 자신의 스키마를 `is_current=true`로 표시해 UI가 기본 선택할 수 있게 한다.

```sql
-- 인증 사용자 자신의 스키마
SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS current_schema FROM dual;
-- 접근 가능한 소유자 목록 (사용자 객체 + 데모용 SH)
SELECT username AS owner FROM ALL_USERS
 WHERE oracle_maintained = 'N' OR username IN ('SH')
 ORDER BY username;
```

- **응답**: `{ "data": { "current_schema": "ADMIN", "owners": [ { "owner": "ADMIN", "is_current": true }, { "owner": "SH", "is_current": false } ] } }`
- UI는 `current_schema`를 스키마 선택기 기본값으로 사용한다 (인증한 스키마에서 보이는 테이블이 곧바로 대상 후보로 노출).

### 8.2 `GET /api/v1/schema/tables?owner=SH`

`owner` 미지정 시 인증 사용자 자신의 스키마(`CURRENT_SCHEMA`)를 기본 대상으로 한다.

```sql
SELECT t.table_name, c.comments, t.num_rows
  FROM ALL_TABLES t LEFT JOIN ALL_TAB_COMMENTS c
    ON c.owner = t.owner AND c.table_name = t.table_name
 WHERE t.owner = :owner ORDER BY t.table_name;
```

- **응답**: `{ "data": [ { "owner": "SH", "table_name": "CUSTOMERS", "comment": null, "num_rows": 55500 } ] }`
- 각 항목은 `{owner, table_name}`을 포함하므로 PG-03a 체크박스 선택이 그대로 `object_list`의 `ObjectRef`(`{owner, name}`)로 매핑된다 (여러 스키마의 테이블을 섞어 선택 가능).

### 8.3 `GET /api/v1/schema/tables/{owner}/{table}/columns`

```sql
SELECT col.column_name, col.data_type, col.nullable, cc.comments
  FROM ALL_TAB_COLUMNS col LEFT JOIN ALL_COL_COMMENTS cc
    ON cc.owner = col.owner AND cc.table_name = col.table_name AND cc.column_name = col.column_name
 WHERE col.owner = :owner AND col.table_name = :table
 ORDER BY col.column_id;
```

---

## 9. Dashboard — 데모 상태 신호등 (FR-09, P1)

### 9.1 `GET /api/v1/dashboard/health`

커넥션·권한·Data Access·기본 프로파일·데모 스키마를 일괄 점검(타임아웃 짧게, 캐시 30초).

```json
{
  "data": {
    "overall": "yellow",
    "signals": [
      { "id": "connection",      "status": "green",  "title_ko": "DB 연결",        "detail_ko": "demoadb_high 접속 정상 (420ms)" },
      { "id": "privileges",      "status": "green",  "title_ko": "권한 점검",       "detail_ko": "필수 항목 전부 통과" },
      { "id": "data_access",     "status": "red",    "title_ko": "Data Access",   "detail_ko": "비활성 — narrate 데모 불가 (ORA-20000)", "fix_endpoint": "POST /api/v1/privileges/apply" },
      { "id": "default_profile", "status": "green",  "title_ko": "기본 프로파일",   "detail_ko": "GENAI_DEMO (ENABLED)" },
      { "id": "demo_schema",     "status": "yellow", "title_ko": "데모 스키마",     "detail_ko": "증강 비교용 모호 스키마 미생성", "fix_endpoint": "POST /api/v1/enrichment/demo-schema" }
    ]
  },
  "executed_sql": ["..."],
  "elapsed_ms": 1300
}
```

---

## 10. Resources — 생성 리소스 대장 CRUD (FR-10)

앱이 생성한 리소스 대장(`~/.selectai/resources.json`, architecture.md §3.3.1)을 기준으로 정리 대상을 보여주고, 개별(DELETE) 또는 일괄(cleanup)로 정리한다. 정리 API는 고객 DB 흔적 제거를 위한 P0 기능이다.

### 10.1 `GET /api/v1/resources` — 대장 목록 조회

- **쿼리 파라미터**
  - `status`: `pending`(기본), `failed`, `done`, `all`
  - `resource_type`: 선택 필터 (`profile`, `credential`, `acl`, `conversation`, `demo_table`, `grant`, `wallet`, `connection`)
- **응답 200**:

```json
{
  "data": {
    "items": [
      {
        "id": "led_01J...",
        "resource_type": "profile",
        "resource_name": "ENRICH_DEMO_ON",
        "owner": "ADMIN",
        "cleanup_order": 20,
        "cleanup_status": "pending",
        "cleanup_preview": "BEGIN DBMS_CLOUD_AI.DROP_PROFILE('ENRICH_DEMO_ON'); END;",
        "created_at": "2026-06-12T10:10:00+09:00"
      }
    ],
    "summary": { "pending": 8, "failed": 0, "done": 3 }
  },
  "executed_sql": [],
  "elapsed_ms": 12
}
```

DB 조회가 아니라 로컬 `~/.selectai/resources.json` 파일 조회이므로 `executed_sql`은 빈 배열이다. 단, `cleanup_preview`에는 실행 예정 SQL 또는 파일 삭제 작업 설명을 마스킹된 문자열로 포함한다.

### 10.2 `DELETE /api/v1/resources/{id}` — 개별 리소스 정리

대장의 단일 항목을 즉시 정리한다. 해당 항목의 `cleanup_preview` SQL(또는 파일 작업)을 실행하고 `cleanup_status`를 갱신한다.

- **응답 200**: `data`에 해당 항목의 정리 결과 1건 (`{ "id", "resource_type", "resource_name", "ok", "status" }` — §10.3 `results[]` 항목과 동일 스키마), `executed_sql`에 실행 SQL 포함
- **오류**: `404 RESOURCE_NOT_FOUND` (대장에 없는 id), `409 RESOURCE_ALREADY_CLEANED` (`status=done` 항목), 정리 SQL 실패 시 200 + `ok=false`/`status=failed` (재시도 가능하도록 항목 유지)
- 대장 항목 자체는 삭제하지 않고 `cleanup_status='done'`으로 남긴다 — 감사 기록 유지. 대장에서 기록 자체를 제거하는 기능은 제공하지 않는다 (흔적 추적이 목적이므로).

### 10.3 `POST /api/v1/resources/cleanup` — 일괄 정리 실행

- **요청**:

```json
{
  "item_ids": ["led_01J...", "led_01K..."],
  "resource_types": ["conversation", "profile", "demo_table"],
  "dry_run": false,
  "include_app_files": true
}
```

- `item_ids`를 지정하면 해당 항목만 정리한다.
- `resource_types`를 지정하면 해당 타입의 `pending`/`failed` 항목을 정리한다.
- 둘 다 생략하면 모든 `pending`/`failed` 항목을 `cleanup_order` 순으로 정리한다.
- `dry_run=true`면 실행 없이 정리 순서와 SQL/작업 설명만 반환한다.
- `include_app_files=false`면 wallet/커넥션 파일 삭제 항목은 `skipped`로 남긴다.

- **응답 200**:

```json
{
  "data": {
    "results": [
      { "id": "led_01J...", "resource_type": "conversation", "resource_name": "30C9...", "ok": true, "status": "done" },
      { "id": "led_01K...", "resource_type": "profile", "resource_name": "ENRICH_DEMO_ON", "ok": false,
        "status": "failed", "error": { "code": "ORA-20404", "app_code": "PROFILE_NOT_FOUND", "message_ko": "지정한 프로파일이 이미 존재하지 않습니다." } }
    ],
    "summary": { "done": 1, "failed": 1, "skipped": 0 }
  },
  "executed_sql": [
    "BEGIN DBMS_CLOUD_AI.DROP_CONVERSATION(:conversation_id); END;",
    "BEGIN DBMS_CLOUD_AI.DROP_PROFILE(:profile_name); END;"
  ],
  "elapsed_ms": 840
}
```

한 항목 실패가 전체 API 실패가 되지 않는다. 실패 항목은 `cleanup_status='failed'`, `last_error`를 기록해 재시도 가능하게 한다. 앱 파일 삭제 작업(wallet 디렉토리 등)은 `executed_sql` 대신 `data.results[].cleanup_action`에 설명을 둔다.

---

## 11. Pydantic 모델 정의

```python
"""Select AI Demo Studio — API 스키마 (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- 공통

class ErrorBody(BaseModel):
    code: str                      # ORA-20000 / DPY-6005 / 앱 코드
    app_code: str                  # DATA_ACCESS_DISABLED 등
    message_ko: str
    hint_ko: Optional[str] = None
    detail: Optional[str] = None
    retryable: bool = False
    executed_sql: list[str] = []
    docs_ref: Optional[str] = None
    candidates: Optional[list["AdbCandidate"]] = None  # ADB_AMBIGUOUS(§2.7) 전용


class ErrorResponse(BaseModel):
    error: ErrorBody


class Envelope(BaseModel):
    """모든 성공 응답의 공통 래퍼. data는 엔드포인트별 모델."""
    data: Any
    executed_sql: list[str] = []   # 비밀 값은 ***MASKED*** 처리 후 노출
    elapsed_ms: int


# ---------------------------------------------------------------- connections

class WalletUploadResult(BaseModel):
    wallet_id: str
    tns_aliases: list[str]
    files_found: list[str]


class WalletGenerateRequest(BaseModel):
    """wallet 자동 다운로드 (§2.7, OCI CLI 경로)."""
    adb_name: str = Field(min_length=1, max_length=255)
    wallet_password: str = Field(repr=False)        # 다운로드 zip에 설정할 암호 — 로그 마스킹
    compartment_id: str = (
        "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq"
    )                                               # 기본: TAEWAN.KIM (CLAUDE.md 전역 규칙)
    oci_profile: str = "DEFAULT"                    # ~/.oci/config 프로파일
    adb_ocid: Optional[str] = None                  # 복수 매칭 후 재호출 시 지정


class WalletGenerateResult(WalletUploadResult):
    """§2.1 업로드와 동일 스키마 + adb_ocid."""
    adb_ocid: str


class AdbCandidate(BaseModel):
    """ADB_AMBIGUOUS(409) 오류의 후보 목록 항목 (§2.7)."""
    adb_ocid: str
    display_name: str
    workload_type: Optional[str] = None


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    wallet_id: str
    tns_alias: str
    username: Literal["admin", "ADMIN"] = "admin"   # v1: admin 고정
    password: str = Field(repr=False)               # 로그/repr 마스킹
    validate_: bool = Field(default=True, alias="validate")


class ConnectionOut(BaseModel):
    id: str
    name: str
    tns_alias: str
    username: str
    db_version: Optional[str] = None
    db_name: Optional[str] = None
    status: Literal["VALID", "INVALID", "UNKNOWN"]
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    db_version: Optional[str] = None
    latency_ms: Optional[int] = None
    app_code: Optional[str] = None
    message_ko: Optional[str] = None
    hint_ko: Optional[str] = None


# ---------------------------------------------------------------- privileges

class CheckStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    not_applicable = "not_applicable"
    unknown = "unknown"


class PrivilegeCheck(BaseModel):
    check_id: str                  # execute_dbms_cloud_ai / network_acl / data_access ...
    title_ko: str
    status: CheckStatus
    description_ko: str
    evidence_sql: Optional[str] = None
    fix_sql: Optional[str] = None  # 적용 전 미리보기 (FR-03)
    docs_ref: Optional[str] = None


class PrivilegeCheckResult(BaseModel):
    provider: str
    target_user: str
    overall: Literal["pass", "action_required"]
    checks: list[PrivilegeCheck]


class CredentialSpec(BaseModel):
    credential_name: str
    auth_type: Literal["api_key", "api_token", "resource_principal"]
    # api_key (OCI 서명 키)
    user_ocid: Optional[str] = None
    tenancy_ocid: Optional[str] = None
    private_key: Optional[str] = Field(default=None, repr=False)
    fingerprint: Optional[str] = None
    # api_token (외부 공급자)
    username: Optional[str] = None
    api_token: Optional[str] = Field(default=None, repr=False)


class PrivilegeApplyItem(BaseModel):
    check_id: str
    credential: Optional[CredentialSpec] = None    # check_id == "credential"
    enable: Optional[bool] = None                  # check_id == "data_access"


class PrivilegeApplyRequest(BaseModel):
    provider: str = "oci"
    target_user: str = "ADMIN"
    items: list[PrivilegeApplyItem]
    recheck: bool = True


class PrivilegeApplied(BaseModel):
    check_id: str
    ok: bool
    executed_sql: str
    error: Optional[ErrorBody] = None


class PrivilegeApplyResult(BaseModel):
    applied: list[PrivilegeApplied]
    recheck: Optional[PrivilegeCheckResult] = None


# ---------------------------------------------------------------- profiles

class ObjectRef(BaseModel):
    owner: str
    name: Optional[str] = None     # 생략 시 스키마 전체


class ProfileAttributes(BaseModel):
    """레퍼런스 §3 검증 21개 속성만 폼 필드로 노출 (R4)."""
    provider: Optional[str] = "oci"
    credential_name: Optional[str] = "OCI$RESOURCE_PRINCIPAL"
    object_list: Optional[list[ObjectRef]] = None
    object_list_mode: Optional[Literal["automated"]] = None
    comments: Optional[Literal["true", "false"]] = None
    annotations: Optional[Literal["true", "false"]] = None
    constraints: Optional[Literal["true", "false"]] = None
    conversation: Optional[Literal["true", "false"]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = "meta.llama-3.3-70b-instruct"
    region: Optional[str] = "us-chicago-1"
    oci_compartment_id: Optional[str] = (
        "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq"
    )
    oci_apiformat: Optional[Literal["GENERIC", "COHERE"]] = None
    oci_endpoint_id: Optional[str] = None
    enforce_object_list: Optional[Literal["true", "false"]] = None
    case_sensitive_values: Optional[Literal["true", "false"]] = None
    target_language: Optional[str] = None
    vector_index_name: Optional[str] = None
    azure_resource_name: Optional[str] = None
    azure_deployment_name: Optional[str] = None
    provider_endpoint: Optional[str] = None


class ProfileCreate(BaseModel):
    profile_name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,127}$")
    attributes: ProfileAttributes
    extra_attributes_json: Optional[str] = None    # 미검증 속성 "고급 JSON" (R4)


class ProfileAttributeOut(BaseModel):
    name: str
    value: Optional[str]
    verified: bool                 # 21개 검증 목록 포함 여부
    description_ko: Optional[str] = None
    docs_ref: Optional[str] = None


class ProfileDetail(BaseModel):
    profile_name: str
    status: Literal["ENABLED", "DISABLED"]
    attributes: list[ProfileAttributeOut]


class ProfileSummary(BaseModel):
    profile_name: str
    status: Literal["ENABLED", "DISABLED"]
    provider: Optional[str] = None
    model: Optional[str] = None
    is_default: bool = False       # 앱 설정 기준 (DB 아님)


class ProfileUpdate(BaseModel):
    attributes: dict[str, Any]     # SET_ATTRIBUTE(S) 대상 (검증/고급 모두 허용, 서버 검증)
    preview_only: bool = False


class DefaultProfileSetting(BaseModel):
    profile_name: str


# ---------------------------------------------------------------- selectai

SelectAIAction = Literal[
    "runsql", "showsql", "explainsql", "narrate", "chat",   # P0
    "showprompt", "feedback",                               # P1
    "summarize", "translate",                               # P2
]   # "showparameter"는 존재하지 않는 액션 — 정의 금지. "agent"는 범위 외.


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    action: SelectAIAction = "runsql"
    profile_name: Optional[str] = None      # None → 앱 기본 프로파일
    conversation_id: Optional[str] = None   # GENERATE params로 전달
    row_limit: int = Field(default=100, ge=1, le=1000)


class GenerateResult(BaseModel):
    action: SelectAIAction
    profile_name: str
    result_type: Literal["table", "sql", "text"]
    generated_sql: Optional[str] = None
    response_text: Optional[str] = None     # GENERATE 반환 CLOB
    columns: Optional[list[str]] = None     # runsql 전용
    rows: Optional[list[list[Any]]] = None
    row_count: Optional[int] = None
    truncated: Optional[bool] = None


class FeedbackRequest(BaseModel):
    profile_name: str
    sql_id: Optional[str] = None            # V$MAPPED_SQL 조회 값
    sql_text: Optional[str] = None          # 프롬프트 전체 텍스트
    feedback_type: Literal["positive", "negative"]
    response: Optional[str] = None          # negative 시 올바른 SQL
    feedback_content: Optional[str] = None
    operation: Literal["add", "delete"] = "add"


# ---------------------------------------------------------------- chat

class ConversationCreate(BaseModel):
    title: str = "Demo chat"
    description: Optional[str] = None
    retention_days: int = 7        # 기본값은 오픈 이슈 O4 결정에 따라 조정
    conversation_length: int = 10


class ConversationOut(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    retention_days: Optional[int] = None
    conversation_length: Optional[int] = None


ConversationAction = Literal["runsql", "showsql", "explainsql", "narrate", "chat"]  # p47 Note


class ChatMessageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    action: ConversationAction = "narrate"
    profile_name: Optional[str] = None


class ChatMessageOut(BaseModel):
    prompt_id: str
    prompt: str
    response: Optional[str] = None
    action: Optional[str] = None
    created_at: Optional[datetime] = None


class ChatCompareRequest(BaseModel):
    prompt: str
    action: ConversationAction = "chat"
    conversation_id: str
    profile_name: Optional[str] = None


class ChatCompareResult(BaseModel):
    without_context: GenerateResult
    with_context: GenerateResult


# ---------------------------------------------------------------- enrichment

class CommentEntry(BaseModel):
    table: str
    column: Optional[str] = None   # None이면 테이블 코멘트
    comment: str = Field(max_length=4000)


class CommentsApplyRequest(BaseModel):
    owner: str = "ADMIN"
    table_comment: Optional[CommentEntry] = None
    column_comments: list[CommentEntry] = []
    preview_only: bool = False


class ProfilePairRequest(BaseModel):
    base_name: str = "ENRICH_DEMO"
    object_list: list[ObjectRef]
    annotations: bool = False      # P1
    constraints: bool = False      # P1


class EnrichCompareRequest(BaseModel):
    prompt: str
    profile_off: str
    profile_on: str
    action: Literal["showsql", "runsql"] = "showsql"
    include_showprompt: bool = False   # P1: 증강 프롬프트에 COMMENT 포함 확인


class EnrichCompareSide(BaseModel):
    profile_name: str
    generated_sql: Optional[str] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    error: Optional[ErrorBody] = None  # 한쪽 실패 허용 (오답 시연이 목적)


class EnrichCompareResult(BaseModel):
    prompt: str
    before: EnrichCompareSide
    after: EnrichCompareSide
    augmented_prompt: Optional[str] = None  # include_showprompt=true 시


# ---------------------------------------------------------------- schema / dashboard

class TableInfo(BaseModel):
    table_name: str
    comment: Optional[str] = None
    num_rows: Optional[int] = None


class ColumnInfo(BaseModel):
    column_name: str
    data_type: str
    nullable: bool
    comment: Optional[str] = None


class HealthSignal(BaseModel):
    id: str
    status: Literal["green", "yellow", "red"]
    title_ko: str
    detail_ko: str
    fix_endpoint: Optional[str] = None


class DashboardHealth(BaseModel):
    overall: Literal["green", "yellow", "red"]
    signals: list[HealthSignal]


# ---------------------------------------------------------------- cleanup

CleanupResourceType = Literal[
    "profile", "credential", "acl", "conversation", "demo_table", "grant", "wallet", "connection", "vector_index"
]


class CleanupLedgerItem(BaseModel):
    id: str
    connection_id: str
    resource_type: CleanupResourceType
    resource_name: str
    owner: Optional[str] = None
    cleanup_order: int
    cleanup_status: Literal["pending", "done", "failed", "skipped"]
    cleanup_preview: str
    created_at: datetime
    cleaned_at: Optional[datetime] = None
    last_error: Optional[str] = None


class CleanupListResult(BaseModel):
    items: list[CleanupLedgerItem]
    summary: dict[str, int]


class CleanupRequest(BaseModel):
    item_ids: Optional[list[str]] = None
    resource_types: Optional[list[CleanupResourceType]] = None
    dry_run: bool = False
    include_app_files: bool = True


class CleanupItemResult(BaseModel):
    id: str
    resource_type: CleanupResourceType
    resource_name: str
    ok: bool
    status: Literal["done", "failed", "skipped", "preview"]
    cleanup_action: Optional[str] = None
    error: Optional[ErrorBody] = None


class CleanupResult(BaseModel):
    results: list[CleanupItemResult]
    summary: dict[str, int]
```

---

## 12. 비동기/타임아웃 전략 (LLM 호출 지연 대응)

### 12.1 실행 모델

| 구분 | 방식 |
|---|---|
| DB 드라이버 | `python-oracledb` **AsyncConnectionPool** (Thin 모드, wallet 디렉토리 지정). FastAPI 비동기 핸들러에서 `await`로 직접 호출 — 이벤트 루프 블로킹 없음 |
| 풀 구성 | 커넥션(conn_id)별 풀 1개: `min=0, max=4, increment=1`. 첫 요청 시 lazy 생성하고, LLM 호출이 DB 세션을 길게 점유하므로 풀을 작게 유지한다. 풀 고갈 시 `503 POOL_EXHAUSTED` (단일 시연자 가정 — PRD 비목표) |
| 세션 무상태 보장 | 풀 반환 전 세션 상태를 만들지 않는 것이 원칙(GENERATE 패턴). 방어적으로 풀 `session_callback`에서 NLS만 설정하고 `SET_PROFILE`류 호출 금지를 코드 리뷰 체크리스트화 (R3) |

### 12.2 계층별 타임아웃

`oracledb`의 `connection.call_timeout`(ms)으로 DB 호출 단위 제한, 초과 시 라운드트립 중단 → `504 LLM_TIMEOUT`으로 변환.

| 작업 | call_timeout | 비고 |
|---|---|---|
| 연결 테스트 (`/connections/{id}/test`) | 5,000 ms | FR-02 수용 기준. `tcp_connect_timeout=5`도 병행 |
| 메타데이터 조회 (schema/profiles/views) | 15,000 ms | |
| 권한 점검/적용 | 30,000 ms | |
| GENERATE — `showsql`/`showprompt` | 60,000 ms | 프롬프트 증강 + LLM 1회 |
| GENERATE — `runsql`/`explainsql`/`narrate`/`chat` | 120,000 ms | LLM + (결과 서술 시 2차 호출 가능) |
| 비교 실행 (`/chat/compare`, `/enrichment/compare`) | 측당 120,000 ms / 총 240,000 ms | 두 호출은 풀 커넥션 2개로 **병렬**(`asyncio.gather`) |
| 데모 스키마 생성/시드 | 60,000 ms | |
| wallet 자동 다운로드 (`/connections/wallet/generate`) | 조회 30,000 ms + 다운로드 120,000 ms | DB 호출 아님 — OCI CLI subprocess(비차단), 초과 시 `504 OCI_CLI_TIMEOUT` (§2.7) |

### 12.3 클라이언트 취소·재시도

- 프론트가 요청을 중단(`AbortController`)하면 FastAPI가 disconnect를 감지해 해당 태스크를 취소하고, 드라이버 `call_timeout`/`connection.cancel()`로 진행 중 DB 호출을 중단한다.
- `retryable: true` 오류(LLM 환각, 타임아웃)는 프론트 "다시 시도" 버튼과 매핑. 서버 측 자동 재시도는 하지 않는다(LLM 비결정성 — 같은 프롬프트 재실행 자체가 데모 가치).
- 멱등성: `POST /selectai/generate`, `POST /chat/.../messages`는 비멱등 — 재시도는 항상 사용자 명시 동작으로만.

### 12.4 장시간 작업

- v1 범위의 모든 호출은 동기 응답(≤120초)으로 처리한다. P2의 합성 데이터 생성(`GENERATE_SYNTHETIC_DATA`)처럼 분 단위 작업이 들어오면 `202 Accepted` + `GET /api/v1/jobs/{job_id}` 폴링 패턴을 도입한다 (v1 미구현, 예약만).
- 챗봇 응답 스트리밍(SSE)은 `DBMS_CLOUD_AI.GENERATE`가 CLOB 일괄 반환이므로 **불가** — UI는 로딩 인디케이터 + `elapsed_ms` 표시로 대응 (FR-06 latency 표시).

### 12.5 동시성 가드

- 동일 conversation_id에 대한 메시지 전송은 서버 측 per-conversation `asyncio.Lock`으로 직렬화 (턴 순서 보장).
- 권한 적용(`/privileges/apply`)과 데모 스키마 생성은 커넥션 단위 전역 Lock — DDL 충돌 방지.

---

## 13. 엔드포인트 인덱스

| # | 메서드 | 경로 | 기능 | FR |
|---|---|---|---|---|
| 1 | POST | `/api/v1/connections/wallet` | wallet zip 업로드 + TNS alias 추출 | FR-01 |
| 1a | POST | `/api/v1/connections/wallet/generate` | wallet 자동 다운로드 (OCI CLI) | FR-01 |
| 2 | POST | `/api/v1/connections` | 커넥션 생성(접속 검증 포함) | FR-01/02 |
| 3 | GET | `/api/v1/connections` | 커넥션 목록 | FR-02 |
| 4 | POST | `/api/v1/connections/{id}/test` | 연결 테스트 (5초 타임아웃) | FR-02 |
| 5 | PATCH | `/api/v1/connections/{id}` | 커넥션 수정 | FR-02 |
| 6 | DELETE | `/api/v1/connections/{id}` | 커넥션 삭제 | FR-02 |
| 7 | GET | `/api/v1/privileges/check` | 권한 사전 점검 (fix_sql 미리보기 포함) | FR-03 |
| 8 | POST | `/api/v1/privileges/apply` | 원클릭 적용 + 자동 재점검 | FR-03 |
| 9 | GET | `/api/v1/profiles/attribute-meta` | 검증 21개 속성 스키마/한국어 해설 | FR-04 |
| 10 | POST | `/api/v1/profiles/preview` | CREATE_PROFILE SQL 미리보기 | FR-04 |
| 11 | POST | `/api/v1/profiles` | 프로파일 생성 | FR-04/05 |
| 12 | GET | `/api/v1/profiles` | 프로파일 목록 | FR-05 |
| 13 | GET | `/api/v1/profiles/{name}` | 속성 상세 (뷰 기반, showparameter 대체) | FR-05 |
| 14 | PATCH | `/api/v1/profiles/{name}` | SET_ATTRIBUTE(S) 수정 | FR-05 |
| 15 | DELETE | `/api/v1/profiles/{name}` | DROP_PROFILE | FR-05 |
| 16 | POST | `/api/v1/profiles/{name}/status` | ENABLE/DISABLE (P1) | FR-05 |
| 17 | GET/PUT | `/api/v1/settings/default-profile` | 앱 수준 기본 프로파일 | FR-05 |
| 18 | GET | `/api/v1/selectai/actions` | 액션 메타데이터 | FR-06 |
| 19 | POST | `/api/v1/selectai/generate` | 액션 실행 (GENERATE 단일 패턴) | FR-06 |
| 20 | POST | `/api/v1/selectai/feedback` | 피드백 (P1) | FR-06 |
| 21 | GET | `/api/v1/selectai/suggested-prompts` | 추천 프롬프트 | FR-06 |
| 22 | POST | `/api/v1/chat/conversations` | CREATE_CONVERSATION | FR-07 |
| 23 | GET | `/api/v1/chat/conversations` | 대화 목록 | FR-07 |
| 24 | POST | `/api/v1/chat/conversations/{id}/messages` | 턴 실행 (params conversation_id) | FR-07 |
| 25 | GET | `/api/v1/chat/conversations/{id}/messages` | 턴 이력 | FR-07 |
| 26 | PATCH | `/api/v1/chat/conversations/{id}` | UPDATE_CONVERSATION | FR-07 |
| 27 | DELETE | `/api/v1/chat/conversations/{id}` | DROP_CONVERSATION | FR-07 |
| 28 | DELETE | `/api/v1/chat/conversations/{id}/messages/{prompt_id}` | 턴 1건 삭제 | FR-07 |
| 29 | POST | `/api/v1/chat/compare` | 맥락 유무 비교 | FR-07 |
| 30 | POST | `/api/v1/enrichment/demo-schema` | 모호 스키마 원클릭 생성 | FR-08 |
| 31 | DELETE | `/api/v1/enrichment/demo-schema` | 데모 스키마 정리 | FR-08 |
| 32 | GET | `/api/v1/enrichment/comments` | 코멘트 조회 | FR-08 |
| 33 | PUT | `/api/v1/enrichment/comments` | 코멘트 적용 (DDL 미리보기) | FR-08 |
| 34 | POST | `/api/v1/enrichment/profile-pair` | comments off/on 프로파일 쌍 생성 | FR-08 |
| 35 | POST | `/api/v1/enrichment/compare` | 전/후 좌우 비교 실행 | FR-08 |
| 36 | GET | `/api/v1/schema/owners` | 접근 가능 스키마 목록 (인증 스키마 `is_current` 표시) | FR-04/08 |
| 37 | GET | `/api/v1/schema/tables` | 테이블 목록 (owner 미지정 시 인증 스키마 기본) | FR-04/08 |
| 38 | GET | `/api/v1/schema/tables/{owner}/{table}/columns` | 컬럼 목록 | FR-04/08 |
| 39 | GET | `/api/v1/dashboard/health` | 데모 상태 신호등 (P1) | FR-09 |
| 40 | GET | `/api/v1/resources` | 생성 리소스 대장 목록 조회 (status/type 필터) | FR-10 |
| 41 | DELETE | `/api/v1/resources/{id}` | 개별 리소스 정리 | FR-10 |
| 42 | POST | `/api/v1/resources/cleanup` | 일괄 정리 실행 + 항목별 결과 반환 | FR-10 |
