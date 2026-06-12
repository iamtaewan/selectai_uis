# Oracle Select AI 기술 레퍼런스 (Select AI Demo Studio 단일 기술 근거 문서)

> **근거 소스**: Oracle® AI Database — *Select AI User's Guide*, Release **26ai**, 문서번호 **G35918-05** (2026년 3월, 259페이지 PDF: `oracle-database-select-ai-users-guide.pdf`).
> 본 문서의 모든 기술 사실(액션명, 프로시저명, 속성명, 권한 SQL)은 위 PDF에서 직접 확인한 내용이다. 페이지 표기는 PDF 절대 페이지 기준.
>
> **중요 — 문서 범위에 대한 주의**: 이 가이드의 Part III ch28(p254–255)은 `DBMS_CLOUD_AI` 패키지의 **서브프로그램 요약 테이블만** 제공하며, 각 프로시저의 전체 파라미터 시그니처와 Profile Attributes 전체 표는 별도 문서(*Autonomous AI Database Supplied Package Reference*)에 있다. 아래 시그니처/파라미터는 본 PDF의 요약·예제에서 확인된 범위까지만 기술했고, 구현 시 파라미터 상세가 추가로 필요하면 Supplied Package Reference를 교차 확인할 것.

---

## 1. Select AI 액션 전체 목록

구문 (ch8, p43):

```sql
SELECT AI <action> <natural_language_prompt>
```

- `SELECT` 다음에 `AI` 키워드. 대소문자 구분 없음. 액션 생략 시 기본값은 `runsql`.
- AI 키워드는 **SELECT 문에서만** 동작. PL/SQL, DDL, DML에는 사용 불가.
- **Database Actions / APEX Service에서는 `SELECT AI` 키워드가 지원되지 않음** → `DBMS_CLOUD_AI.GENERATE` 함수를 사용해야 함 (p44). 웹 앱(FastAPI) 백엔드도 stateless 커넥션이라면 `GENERATE` 사용이 정석 (p42 Note).
- 프로파일 미설정 상태에서 `SELECT AI` 실행 시 오류: `ORA-00923: FROM keyword not found where expected` (p45).
- 프롬프트에 작은따옴표가 있으면 두 번 입력: `select ai how many customers in SF don''t own their own home` (p45).

### 액션 표 (ch8, p43–44 공식 표)

| 액션 키워드 | 동작 |
|---|---|
| `runsql` | **기본 액션.** 자연어 프롬프트로 SQL을 생성하고 즉시 실행하여 결과를 반환. RAG도 지원. 액션 키워드 생략 가능 |
| `showsql` | 자연어 프롬프트에 대해 생성된 SQL 문장만 표시 (실행하지 않음) |
| `explainsql` | 생성된 SQL을 LLM에 보내 자연어 설명을 함께 반환. `showsql`보다 상세한 설명 제공 (p45) |
| `narrate` | NL2SQL: SQL 실행 결과(실제 데이터)를 LLM에 보내 자연어 서술로 변환. RAG: 벡터 스토어 검색 결과 기반 응답. 관리자(`DISABLE_DATA_ACCESS`)가 데이터 전송을 차단하면 narrate는 비활성화됨 |
| `chat` | 프롬프트를 LLM에 직접 전달(pass-through). `conversation: true`면 이전 대화 맥락 포함 |
| `showprompt` | LLM에 전송될 **증강 프롬프트(constructed prompt)를 표시**. NL2SQL·RAG 지원, synthetic data·explainsql·narrate는 미지원 |
| `summarize` | `SELECT AI SUMMARIZE <TEXT>`로 텍스트 요약 생성. 커스터마이즈는 `DBMS_CLOUD_AI.SUMMARIZE` 함수 사용 |
| `feedback` | 자연어로 생성 SQL에 대한 피드백 제공 → 이후 SQL 생성 정확도 개선. **26ai 전용.** `runsql`/`showsql`/`explainsql`과 함께 사용. RAG 프로파일에서는 사용 불가 |
| `translate` | OCI 번역 서비스를 통해 프롬프트를 `target_language` 속성에 지정된 언어로 번역. **provider가 oci일 때만 지원** (p188) |
| `agent` | 자연어 프롬프트를 Select AI Agent 팀에 전달 (Part II, `DBMS_CLOUD_AI_AGENT`) |

### `showparameter` 액션 존재 여부 판정

- **`showparameter`라는 액션은 PDF 어디에도 존재하지 않는다** (ch8 액션 표 및 전체 본문 확인).
- 가장 가까운 실제 기능:
  1. **`showprompt` 액션** — LLM에 전송되는 증강 프롬프트(스키마 메타데이터 포함)를 보여줌. "내부 동작 들여다보기" 데모 목적이라면 이것이 정답.
  2. **프로파일 속성 조회** — `USER_CLOUD_AI_PROFILE_ATTRIBUTES` / `DBA_CLOUD_AI_PROFILE_ATTRIBUTES` 뷰 조회, 또는 `DBMS_CLOUD_AI.GET_PROFILE()` 함수(현재 세션 프로파일명 반환).
- 데모 UI에는 `showprompt`를 액션 목록에 포함하고, "showparameter"는 사용하지 않을 것.

### 액션 사용 예시 (ch19 p75–76, SH 스키마)

```sql
select ai how many customers exist;                  -- runsql(기본)
select ai showsql how many customers exist;
select ai narrate how many customers exist;
select ai chat how many customers exist;
select ai explainsql how many customers in San Francisco are married;
select ai feedback for query "select ai showsql how many watch histories in total", please use sum instead of count;
select ai feedback the result is correct;            -- 마지막 AI SQL에 대한 긍정 피드백
SELECT AI SUMMARIZE <긴 텍스트>;
select ai translate I need to translate this;        -- target_language 속성 필요
```

---

## 2. DBMS_CLOUD_AI 핵심 프로시저/함수 (ch28, p254–255 + 예제 검증)

### 프로파일 관리

| 서브프로그램 | 설명 |
|---|---|
| `CREATE_PROFILE` (Procedure) | AI 프로파일 생성. `profile_name`, `attributes`(JSON CLOB) 파라미터 |
| `SET_PROFILE` (Procedure) | 현재 세션에 프로파일 활성화. **stateful 세션마다 다시 실행해야 함.** stateless 환경에서는 `GENERATE`에 profile_name을 직접 지정 (p42) |
| `GET_PROFILE` (Function) | 현재 세션 프로파일명 반환: `SELECT DBMS_CLOUD_AI.GET_PROFILE() FROM dual;` |
| `CLEAR_PROFILE` (Procedure) | 현재 세션의 활성 프로파일 해제 |
| `ENABLE_PROFILE` / `DISABLE_PROFILE` (Procedure) | 데이터베이스 수준에서 프로파일 사용 가능/불가 전환 |
| `DROP_PROFILE` (Procedure) | 프로파일 삭제: `EXEC DBMS_CLOUD_AI.DROP_PROFILE('GENAI');` |
| `SET_ATTRIBUTE` (Procedure) | 프로파일 속성 1개 변경 |
| `SET_ATTRIBUTES` (Procedure) | JSON 이름·값 쌍으로 속성 여러 개 변경 |

### 실행

| 서브프로그램 | 설명 |
|---|---|
| `GENERATE` (Function) | **stateless 호출용 핵심 함수.** 데모 백엔드(FastAPI)에서 사용할 기본 API. 확인된 파라미터: `prompt`, `profile_name`, `action`, `params`(JSON, 예: `{"conversation_id":"..."}`), `attributes`(translate용 `{"target_language":"fr","source_language":"en"}`) |
| `GENERATE_SYNTHETIC_DATA` (Function) | 합성 데이터 생성. 확인된 파라미터: `profile_name`, `object_name`, `owner_name`, `record_count`, `user_prompt`, `object_list`(JSON 배열, 항목별 `owner`/`name`/`record_count`/`user_prompt`) |
| `SUMMARIZE` (Function) | 요약 생성. 확인된 파라미터: `content`(CLOB), `location_uri`, `credential_name`, `profile_name`, `user_prompt`, `params`(JSON: `min_words`, `max_words`, `summary_style`("list" 등), `chunk_processing_method`("iterative_refinement"/MapReduce, 기본 MapReduce)) |
| `TRANSLATE` (Function) | 텍스트 번역. 확인된 파라미터: `profile_name`, `text`, `source_language`, `target_language` |
| `FEEDBACK` (Procedure) | SQL 생성 정확도 개선 피드백. 확인된 파라미터: `profile_name`, `sql_id`(V$MAPPED_SQL에서 조회) 또는 `sql_text`(프롬프트 전체), `feedback_type`('positive'/'negative'), `response`(올바른 SQL), `feedback_content`(자연어 설명), `operation`('add'/'delete'). sql_id당 피드백 1건만 유지(재제출 시 교체) |

`GENERATE` 호출 예 (p129):

```sql
SELECT DBMS_CLOUD_AI.GENERATE(
        prompt       => 'What is the difference in weather between Seattle and San Francisco?',
        profile_name => 'GENAI',
        action       => 'CHAT',
        params       => '{"conversation_id":"30C9DB6E-EA4D-AFBA-E063-9C6D46644B92"}') AS RESPONSE;
```

### 대화(Conversations) 관리 (p127–135, p254–255)

| 서브프로그램 | 설명 |
|---|---|
| `CREATE_CONVERSATION` (Function) | 대화 생성 후 conversation_id(UUID 문자열) 반환. 선택적 `attributes` JSON: `title`, `description`, `retention_days`, `conversation_length` |
| `CREATE_CONVERSATION` (Procedure) | 대화 생성과 동시에 현재 세션에 설정 |
| `SET_CONVERSATION_ID` (Procedure) | 세션에 대화 ID 설정 → 이후 `SELECT AI <action> <prompt>`가 해당 대화 맥락 사용 |
| `GET_CONVERSATION_ID` (Function) | 현재 세션에 설정된 대화 ID 반환 |
| `CLEAR_CONVERSATION_ID` (Function) | 세션의 대화 ID 해제 |
| `UPDATE_CONVERSATION` (Procedure) | `conversation_id` + `attributes` JSON으로 title/description/retention_days/conversation_length 수정 |
| `DELETE_CONVERSATION_PROMPT` (Procedure) | 특정 프롬프트 1건 삭제 (conversation_prompt_id 지정) |
| `DROP_CONVERSATION` (Procedure) | 대화 전체와 프롬프트 삭제 |

### 데이터 액세스 제어 (p174–176)

| 서브프로그램 | 설명 |
|---|---|
| `ENABLE_DATA_ACCESS` (Procedure) | LLM으로 실제 데이터 전송 허용 (기본). **관리자(ADMIN) 실행** |
| `DISABLE_DATA_ACCESS` (Procedure) | LLM으로 실제 데이터 전송 차단. `narrate` 액션과 합성 데이터 생성이 `ORA-20000: Data access is disabled for SELECT AI` 오류 발생. NL2SQL(runsql/showsql)은 계속 동작 |

### 벡터 인덱스(RAG) 관리

`CREATE_VECTOR_INDEX`, `DROP_VECTOR_INDEX`, `ENABLE_VECTOR_INDEX`, `DISABLE_VECTOR_INDEX`, `UPDATE_VECTOR_INDEX` (p255). RAG는 데모 선택 기능이므로 상세는 ch11/ch19 RAG 예제(p135 이후) 참조.

### 관련 뷰 (ch29, p256)

| 뷰 | 용도 |
|---|---|
| `USER_CLOUD_AI_PROFILES` / `DBA_CLOUD_AI_PROFILES` | 프로파일 목록 (데모 "프로파일 목록" 화면의 데이터 소스) |
| `USER_CLOUD_AI_PROFILE_ATTRIBUTES` / `DBA_CLOUD_AI_PROFILE_ATTRIBUTES` | 프로파일 속성 조회 ("showparameter" 대체 기능) |
| `USER_CLOUD_AI_CONVERSATIONS` / `DBA_CLOUD_AI_CONVERSATIONS` | 대화 목록 (DBA_ 뷰는 ADMIN 전용) |
| `USER_CLOUD_AI_CONVERSATION_PROMPTS` / `DBA_CLOUD_AI_CONVERSATION_PROMPTS` | 대화별 프롬프트 이력 |
| `USER_CLOUD_VECTOR_INDEXES`, `..._ATTRIBUTES` | 벡터 인덱스 목록/속성 |
| `AI_TRANSLATION_LANGUAGES` | 번역 지원 언어 목록 (LANGUAGE_NAME, LANGUAGE_CODE, PROVIDER) |
| `V$MAPPED_SQL` (`v$cloud_ai_sql`도 예제에 등장, p181) | `select ai` 프롬프트의 SQL_ID 조회 (Feedback용) |

---

## 3. AI Profile 속성(attributes) — PDF에서 확인된 전체 목록

`CREATE_PROFILE`의 `attributes` 파라미터는 JSON 문자열. 아래는 본 PDF 본문·예제에서 실제로 확인된 속성과 데모 UI용 한국어 해설이다. (전체 공식 속성 표는 Supplied Package Reference의 "Profile Attributes" 절 — PDF는 해당 외부 절을 참조하도록 안내함)

| 속성 | 의미 / UI 한국어 해설 | 비고(확인 페이지) |
|---|---|---|
| `provider` | AI 공급자. 앱 P0 UI에서 검증해 제공하는 선택지는 `"oci"`(OCI Generative AI), `"openai"`, `"azure"`, `"google"`, `"cohere"`, `"anthropic"`, `"aws"`이다. **OpenAI 호환 공급자는 `provider` 대신 `provider_endpoint`로 지정** | p17, p78 등 |
| `credential_name` | AI 공급자 접근 자격증명 이름. `DBMS_CLOUD.CREATE_CREDENTIAL`로 생성. OCI Resource Principal 사용 시 `"OCI$RESOURCE_PRINCIPAL"` | p81 |
| `object_list` | NL2SQL 대상 객체의 JSON 배열. `[{"owner":"SH","name":"customers"}, ...]` 또는 스키마 전체 `[{"owner":"SH"}]`. 외부 테이블(데이터 레이크)도 지정 가능. **미지정 시 현재 스키마의 모든 객체를 자동 선택** | p78, p151 |
| `object_list_mode` | `"automated"` 설정 시 26ai에서 질의와 관련 있는 테이블 메타데이터만 자동 탐지·전송. `<profile_name>_OBJECT_LIST_VECINDEX` 벡터 인덱스를 자동 생성 | p151–152 |
| `comments` | `"true"`면 테이블/컬럼 COMMENT를 LLM 메타데이터에 포함 → SQL 생성 정확도 향상. **데모 핵심 속성(전/후 비교 시연)** | p147–149 |
| `annotations` | `"true"`면 26ai 테이블/컬럼 ANNOTATIONS를 메타데이터에 포함 | p149 |
| `constraints` | `"true"`면 FK/참조 무결성 제약을 메타데이터에 포함 → JOIN 정확도 향상 | p150 |
| `conversation` | `"true"/"false"`. 세션 기반 단기 대화 활성화(최근 프롬프트 최대 10개를 증강 프롬프트에 포함). 명시적 conversation_id를 쓰면 이 설정은 무시됨 | p47, p93 |
| `temperature` | LLM 샘플링 온도(낮을수록 결정적). 예제 값 `0.2` | p136 |
| `max_tokens` | 응답 최대 토큰 수. 예제 값 `4096` | p136 |
| `model` | 모델명. OCI 예: `"meta.llama-3.3-70b-instruct"`, `"cohere.command-r-plus-08-2024"`, `"xai.grok-3"`. 모델 OCID도 지정 가능(이때 `oci_apiformat` 필요) | p84, p91–92 |
| `region` | OCI Generative AI 호출 리전. 예: `"eu-frankfurt-1"`. 미지정 시 기본 리전(가이드 기본값은 us-chicago-1 계열 OCI GenAI 리전) | p84 |
| `oci_compartment_id` | OCI Generative AI를 호출할 컴파트먼트 OCID | p85 |
| `oci_apiformat` | OCI GenAI API 포맷. Meta Llama/Generic 모델 엔드포인트는 `"GENERIC"`, Cohere 모델은 `"COHERE"` | p89, p91–92 |
| `oci_endpoint_id` | OCI GenAI 전용(Dedicated) 모델 엔드포인트 ID. `model` 대신 지정 | p91 |
| `enforce_object_list` | `"true"`면 LLM이 object_list에 나열된 테이블만 사용하도록 제한. `"false"`면 LLM 사전 지식 기반 다른 테이블/뷰도 사용 가능 | p190–191 |
| `case_sensitive_values` | `"false"`면 `UPPER()` 비교 등 대소문자 무시 SQL 생성. 프롬프트에서 큰따옴표로 감싸면 개별적으로 대소문자 구분 가능 | p191–192 |
| `target_language` | translate 액션의 목표 언어 (provider oci 전용). 예: `"french"` | p188 |
| `vector_index_name` | RAG용 벡터 인덱스 이름. 지정 시 narrate가 벡터 검색 기반 응답 생성 | p136 |
| `azure_resource_name` / `azure_deployment_name` | Azure OpenAI 전용 리소스/배포 이름 | p148 |
| `provider_endpoint` | OpenAI 호환 공급자(Fireworks AI 등)의 베이스 URL. `provider` 대신 사용 | p17, p41 |

대화 속성(프로파일이 아닌 `CREATE_CONVERSATION`/`UPDATE_CONVERSATION`의 attributes): `title`, `description`, `retention_days`, `conversation_length` (p127).

---

## 4. 사전 요구 권한 (ch7 "Perform Prerequisites for Select AI", p33–37)

필요 요소: ① OCI 계정 + Autonomous AI Database 인스턴스, ② AI 공급자 계정(API 키), ③ 네트워크 ACL(외부 공급자만), ④ 자격증명(credential).

### 4.1 EXECUTE 권한 (관리자=ADMIN이 실행)

```sql
-- Select AI 기본
GRANT EXECUTE ON DBMS_CLOUD_AI TO ADB_USER;

-- RAG 사용 시 추가
GRANT EXECUTE ON DBMS_CLOUD_PIPELINE TO ADB_USER;
```

- 기본적으로 시스템 관리자만 EXECUTE 권한 보유. `DWROLE` 롤이 있으면 `DBMS_CLOUD_PIPELINE`은 이미 포함 (p34).
- 권한 점검 쿼리 (p35) — 데모의 "권한 설정 확인" 기능에 그대로 사용 가능:

```sql
SELECT table_name AS package_name, privilege
  FROM DBA_TAB_PRIVS
 WHERE grantee = '<username>'
   AND (table_name = 'DBMS_CLOUD_PIPELINE' OR table_name = 'DBMS_CLOUD_AI');
```

### 4.2 네트워크 ACL (DBMS_NETWORK_ACL_ADMIN)

> **Note (p34): OCI Generative AI에는 네트워크 ACL이 필요 없다.** 외부 공급자(OpenAI 등)를 쓸 때만 필요. 데모 기본 프로바이더가 OCI GenAI이므로 ACL 단계는 "외부 공급자 선택 시"로 분기 처리할 것.

```sql
BEGIN
    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host => 'api.openai.com',
        ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                            principal_name => 'ADB_USER',
                            principal_type => xs_acl.ptype_db)
    );
END;
/
```

공급자별 host (p36): OpenAI `api.openai.com`, Cohere `api.cohere.ai`, Azure `<azure_resource_name>.openai.azure.com`, Google `generativelanguage.googleapis.com`, Anthropic `api.anthropic.com`, Hugging Face `api-inference.huggingface.co`, AWS `bedrock-runtime.us-east-1.amazonaws.com`.

> X5 결정: PDF의 ACL host 목록에는 Hugging Face host가 등장하지만, P0에서 사용할 `provider` 속성 문자열은 본 문서 범위에서 확정하지 않는다. 따라서 UI provider enum에는 넣지 않고, 필요 시 `provider_endpoint` 또는 고급 JSON 입력으로 우회한다.

### 4.3 자격증명 생성 (DBMS_CLOUD.CREATE_CREDENTIAL)

API 키 방식(외부 공급자, username/password형):

```sql
EXEC DBMS_CLOUD.CREATE_CREDENTIAL(
  credential_name => 'OPENAI_CRED',
  username        => 'OPENAI',
  password        => '<your_api_token>');
```

OCI API 서명 키 방식(OCI GenAI):

```sql
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'GENAI_CRED',
    user_ocid       => 'ocid1.user.oc1..aaaa...',
    tenancy_ocid    => 'ocid1.tenancy.oc1..aaaa...',
    private_key     => '<your_api_key>',
    fingerprint     => '<your_fingerprint>');
END;
/
```

### 4.4 Resource Principal (OCI GenAI, 자격증명 없이 인증) (p81)

1. OCI 테넌시 관리자: Dynamic Group 생성 후 정책 부여:

```text
allow dynamic-group <your-dynamic-group-name> to manage generative-ai-family in tenancy
-- 또는 컴파트먼트 한정
allow dynamic-group <your-dynamic-group-name> to manage generative-ai-family in compartment <your-compartment-name>
```

2. DB 관리자(ADMIN)로 접속하여 Resource Principal 활성화 — **이 PDF에서 확인된 프로시저명은 `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH`** (ENABLE_RESOURCE_PRINCIPAL이라는 이름은 본 가이드에 등장하지 않음):

```sql
BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI');
END;
/
```

3. 프로파일에서 `"credential_name": "OCI$RESOURCE_PRINCIPAL"` 사용.

### 4.5 기타 권한

```sql
-- RAG: 벡터 인덱스용 테이블스페이스 쿼터 (p37)
ALTER USER ADB_USER QUOTA 1T ON <tablespace_name>;

-- Feedback에서 "마지막 AI SQL" 참조 시 (p64)
GRANT READ ON SYS.V_$MAPPED_SQL TO ADB_USER;
GRANT READ ON SYS.V_$SESSION TO ADB_USER;

-- Translate: IAM 정책 (p187)
-- allow group <your group name> to use ai-service-language-family in compartment <your_compartment>
```

> 데모는 DB 사용자 `admin`으로 접속하므로 EXECUTE grant 자체는 불필요할 수 있으나, "권한 점검+적용" 시연 기능을 위해 위 SQL을 그대로 구현할 것. `DISABLE/ENABLE_DATA_ACCESS`, `DBA_` 뷰, `ENABLE_PRINCIPAL_AUTH`는 ADMIN 권한 필요.

---

## 5. OCI Generative AI 프로바이더 설정 (데모 기본값)

### 인증 방식 2가지

1. **API 서명 키(credential)** — `DBMS_CLOUD.CREATE_CREDENTIAL`(user_ocid/tenancy_ocid/private_key/fingerprint) → `credential_name` 지정.
2. **Resource Principal** — `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI')` + IAM Dynamic Group 정책 → `"credential_name": "OCI$RESOURCE_PRINCIPAL"`. ACL·키 관리가 필요 없어 데모 환경에 적합.

### 지원 모델 (ch2 표, p15)

- **Chat 모델 (모든 액션 지원: runsql, showsql, explainsql, narrate, chat)**: `meta.llama-3.3-70b-instruct`(**기본값**), `meta.llama-3.2-90b-vision-instruct`, `meta.llama-3.2-11b-vision-instruct`, `meta.llama-3.1-70b-instruct`, `meta.llama-3.1-405b-instruct`, `cohere.command-r-08-2024`, `cohere.command-r-plus-08-2024`, `cohere.command-r-16k`(deprecated), `cohere.command-r-plus`(deprecated), `xai.grok-3`, `xai.grok-3-fast`, `xai.grok-3-mini`, `xai.grok-3-mini-fast`, `xai.grok-4`, `xai.grok-4-fast-reasoning`, `xai.grok-4-fast-non-reasoning`
- OCI **Generate text** 모델은 `chat` 액션 전용.
- **임베딩(RAG)**: `cohere.embed-english-v3.0`(기본), `cohere.embed-multilingual-v3.0`, `cohere.embed-english-light-v3.0`, `cohere.embed-multilingual-light-v3.0`
- `model` 미지정 시 기본 모델 자동 사용 (p91).

### 완전한 CREATE_PROFILE 예제 (p84–85, 데모 컴파트먼트 적용)

```sql
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => 'GENAI',
      attributes   => '{"provider": "oci",
        "credential_name": "OCI$RESOURCE_PRINCIPAL",
        "object_list": [{"owner": "SH", "name": "customers"},
                        {"owner": "SH", "name": "countries"},
                        {"owner": "SH", "name": "supplementary_demographics"},
                        {"owner": "SH", "name": "profits"},
                        {"owner": "SH", "name": "promotions"},
                        {"owner": "SH", "name": "products"}],
        "model": "meta.llama-3.3-70b-instruct",
        "region": "us-chicago-1",
        "oci_compartment_id": "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq",
        "conversation": "true",
        "comments": "true"
       }');
END;
/

EXEC DBMS_CLOUD_AI.SET_PROFILE('GENAI');
SELECT DBMS_CLOUD_AI.GET_PROFILE() FROM dual;
```

- Llama/Grok 계열을 전용 엔드포인트로 쓸 때는 `"oci_apiformat": "GENERIC"`, Cohere 모델 OCID는 `"COHERE"` (p89–92).
- 정리: `EXEC DBMS_CLOUD_AI.CLEAR_PROFILE;` → `EXEC DBMS_CLOUD_AI.DROP_PROFILE('GENAI');`

---

## 6. Conversations / 챗봇 통합 (ch10 p47–49, ch19 p124–135)

### 두 가지 대화 유형

| | 세션 기반 단기 대화 | 커스터마이즈 장기 대화 |
|---|---|---|
| 활성화 | 프로파일 속성 `{"conversation": "true"}` | `CREATE_CONVERSATION` + `SET_CONVERSATION_ID` 또는 `GENERATE`의 `params`에 `conversation_id` |
| 저장 | 세션 임시 테이블(세션 종료 시 삭제, 재사용 불가) | 영구 테이블, 다중 세션·다중 대화 지원 |
| 개수 | 1개 | 여러 개, ID로 전환 가능 |
| 맥락 | 최근 프롬프트 최대 10개를 증강 프롬프트에 포함 | `conversation_length`로 길이 제어 |

- 두 방식 동시 사용 시 명시적 conversation_id가 우선하고 `conversation` 설정은 무시됨 (p47).
- **대화가 지원하는 액션: `runsql`, `showsql`, `explainsql`, `narrate`, `chat`** (p47 Note).

### 챗봇 구현 플로우 (데모 권장: stateless 백엔드 → GENERATE + conversation_id)

```sql
-- 1) 대화 생성 (UUID 반환; 19c에서는 FROM dual 필요)
SELECT DBMS_CLOUD_AI.CREATE_CONVERSATION(
         attributes => '{"title":"Demo chat",
                         "description":"Select AI demo conversation",
                         "retention_days":5,
                         "conversation_length":5}') FROM dual;

-- 2) 매 턴: GENERATE에 conversation_id 전달 (세션 독립적)
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => '<사용자 메시지>',
         profile_name => 'GENAI',
         action       => 'CHAT',            -- 또는 RUNSQL/NARRATE 등
         params       => '{"conversation_id":"<uuid>"}') AS RESPONSE;

-- (세션 기반 대안) EXEC DBMS_CLOUD_AI.SET_CONVERSATION_ID('<uuid>'); 후 SELECT AI <action> <prompt>;

-- 3) 관리
SELECT DBMS_CLOUD_AI.GET_CONVERSATION_ID;                       -- 현재 세션 대화 확인
EXEC DBMS_CLOUD_AI.UPDATE_CONVERSATION('<uuid>', attributes => '{"title":"a title","retention_days":20}');
EXEC DBMS_CLOUD_AI.DELETE_CONVERSATION_PROMPT('<prompt_uuid>'); -- 프롬프트 1건 삭제
EXEC DBMS_CLOUD_AI.DROP_CONVERSATION('<uuid>');                 -- 대화 종료(전체 삭제)

-- 4) 이력 조회 (챗봇 히스토리 화면)
SELECT conversation_id, conversation_title, description, retention_days, conversation_length
  FROM USER_CLOUD_AI_CONVERSATIONS;
SELECT * FROM USER_CLOUD_AI_CONVERSATION_PROMPTS WHERE conversation_id = '<uuid>';
```

- conversation_id 없이 `GENERATE(action=>'CHAT')`를 호출하면 맥락 없는 응답이 반환됨 (p132) — 데모에서 "대화 없음 vs 대화 있음" 비교 시연 가능.

---

## 7. Comment / Metadata Enrichment (NL2SQL 정확도 증강)

### 개념 (ch4 p25–26)

- **Metadata Enrichment**: 스키마에 고품질 설명·코멘트·애너테이션을 보강해 LLM이 테이블/컬럼의 비즈니스 의미를 이해하고 더 정확한 SQL을 생성하게 하는 실천법.
- Select AI는 NL2SQL 프롬프트를 테이블 정의(테이블명, 컬럼명, 데이터 타입)로 증강하며, **옵션으로 테이블·컬럼 comments, annotations, constraints를 포함**시킨다 (p25).
- SQL 생성 시 DB는 스키마 메타데이터만 LLM에 보낸다(실제 행 데이터는 전송 안 함; narrate만 예외) (p14 Usage Guidelines).
- 권장 보강 내용: 테이블/컬럼 목적·단위·허용값 범위, PK/FK·조인 경로, 동의어·별칭, 샘플 값/필터 패턴 (p26).

### 전/후 비교 데모 시나리오 (ch19 "Example: Improve SQL Query Generation", p147–150)

1단계 — COMMENT 추가:

```sql
COMMENT ON TABLE table1 IS 'Contains movies, movie titles and the year it was released';
COMMENT ON COLUMN table1.c1 IS 'movie ids. Use this column to join to other tables';
COMMENT ON COLUMN table1.c2 IS 'movie titles';
COMMENT ON COLUMN table1.c3 IS 'year the movie was released';
COMMENT ON COLUMN table2.c7 IS 'number of views, watched, streamed';
-- (c1~c7 등 모호한 컬럼명에 의미를 부여)
```

2단계 — 프로파일에 `"comments":"true"` 활성화:

```sql
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'myprofile',
    attributes => '{"provider": "oci",
      "credential_name": "GENAI_CRED",
      "comments": "true",
      "object_list": [
        {"owner": "moviestream", "name": "table1"},
        {"owner": "moviestream", "name": "table2"},
        {"owner": "moviestream", "name": "table3"}]
      }');
  DBMS_CLOUD_AI.SET_PROFILE(profile_name => 'myprofile');
END;
/

select ai showsql what are our total views;          -- 코멘트 기반으로 c7(views) 정확히 매핑
select ai what are our total views broken out by device;
```

3단계 — 비교 포인트: 컬럼명이 c1~c7처럼 무의미할 때 comments 미사용 프로파일은 잘못된 컬럼(QUANTITY_SOLD 등)을 선택하지만, comments 사용 시 의도한 컬럼으로 정확한 SQL 생성.

### 관련 증강 기능

- **Annotations** (26ai): `CREATE TABLE ... ANNOTATIONS (display 'lastname')` 후 프로파일 `"annotations":"true"` (p149).
- **Constraints**: FK/참조 제약을 메타데이터로 전송해 JOIN 정확도 향상 — `"constraints":"true"` (p150).
- **Automated object list** (26ai): `"object_list_mode":"automated"` — 질의 관련 테이블만 자동 선별, `<profile_name>_OBJECT_LIST_VECINDEX` 자동 생성, `UPDATE_VECTOR_INDEX`로 `refresh_rate`/`similarity_threshold`/`match_limit` 조정 (p151).
- 일반 가이드: "컨텍스트가 드러나는 컬럼명을 가진 뷰/테이블을 쓰거나 컬럼 코멘트 추가를 고려하라" (p45 Usage Notes).
- 합성 데이터에도 COMMENT 활용 가능: `COMMENT ON COLUMN EMPLOYEES.state IS 'the value for state should either be CA, WA, or TX'` → 생성 값 제약 (p174).

---

## 8. 데모에 유용한 부가 기능 (선택 기능 후보)

| 기능 | 요약 | 핵심 API |
|---|---|---|
| **Feedback** (ch14, p63–65; 예제 p176–182) | 생성 SQL에 긍정/부정 피드백 → `<profile_name>_FEEDBACK_VECINDEX` 벡터 인덱스에 저장, 유사 프롬프트의 힌트로 재사용되어 정확도 개선. 26ai 전용, NL2SQL 프로파일에서만. sql_id당 1건 유지 | `select ai feedback ...` / `DBMS_CLOUD_AI.FEEDBACK` |
| **Summarize** (ch15, p66–67; 예제 p182–187) | 최대 1GB 텍스트 요약. 청크 처리 기법: MapReduce(기본)/Iterative Refinement. `min_words`, `max_words`, `summary_style`("list"), `user_prompt` 커스터마이즈 | `SELECT AI SUMMARIZE <text>` / `DBMS_CLOUD_AI.SUMMARIZE` |
| **Translate** (ch16, p68–69; 예제 p187–190) | OCI Language 서비스 기반 번역. provider oci 전용. IAM 정책 `ai-service-language-family` 필요. 지원 언어는 `AI_TRANSLATION_LANGUAGES` 뷰 | `select ai translate <text>` / `DBMS_CLOUD_AI.TRANSLATE` / `GENERATE(action=>'translate', attributes=>'{"target_language":"fr","source_language":"en"}')` |
| **Synthetic Data Generation** (ch13, p59–62; 예제 p172–174) | 스키마에 맞는 합성 데이터 생성(테이블별 record_count, user_prompt 지정). 진행 상태는 `SYNTHETIC_DATA$<operation_id>_STATUS` 테이블과 `USER_LOAD_OPERATIONS`로 모니터링 | `DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA` |
| **RAG / Vector Index** (ch11; 예제 p135–147) | 오브젝트 스토리지 문서 → 벡터 인덱스 → `narrate`가 출처(Sources) 포함 응답. `DBMS_CLOUD_PIPELINE` EXECUTE + 테이블스페이스 쿼터 필요 | `CREATE_VECTOR_INDEX`, 프로파일 `vector_index_name` |
| **Data Access 제어** (p174–176) | LLM으로의 실데이터 전송 on/off 거버넌스 시연 | `ENABLE_DATA_ACCESS` / `DISABLE_DATA_ACCESS` |
| **enforce_object_list / case_sensitive_values** (p190–192) | 테이블 접근 제한·대소문자 무시 비교 시연 | 프로파일 속성 |
| **Select AI Agent** (Part II, ch20–27) | `select ai agent <prompt>`, `DBMS_CLOUD_AI_AGENT` 패키지(에이전트/태스크/툴/팀). 데모 범위 외 참고 |

---

## 9. 권장 데모 스키마

PDF 예제가 일관되게 사용하는 스키마:

1. **SH (Sales History)** — 대부분의 NL2SQL 예제 표준. object_list 구성: `customers`, `countries`, `supplementary_demographics`, `profits`, `promotions`, `products` (p78). 대표 데모 프롬프트:
   - `how many customers exist` (55500)
   - `how many customers in San Francisco are married`
   - `what are the top 3 customers in San Francisco` (narrate)
   - 대화형: `what are the total number of customers` → `break out count of customers by country` → `what age group is most common` → `keep the top 5 customers and their country by their purchases and include a rank in the result` (p125–126)
2. **moviestream / ADB_USER 무비 스키마** — comments/annotations/feedback/합성 데이터 예제용: `movies`, `genres`, `movie_genres`, `watch_history`, `users`, `streams`, `customer`, `director`, `actor`, `movie_actor` 등 (p147–181). **Comment 전/후 비교 데모는 일부러 모호한 컬럼명(c1, c2, …)을 가진 소형 무비 테이블을 만들어 시연하는 것이 PDF 방식과 일치.**

---

## 10. 데모 앱 구현 시 주의사항 (PDF 근거 요약)

1. `SET_PROFILE`/`SET_CONVERSATION_ID`는 **세션 상태**다. FastAPI + 커넥션 풀(stateless) 구조에서는 `DBMS_CLOUD_AI.GENERATE(profile_name=>..., params=>'{"conversation_id":...}')` 패턴을 기본으로 설계할 것 (p42, p44).
2. OCI Generative AI는 **네트워크 ACL 불필요** (p34). ACL 자동 적용 로직은 외부 공급자 선택 시에만 실행.
3. `DISABLE_DATA_ACCESS` 상태에서는 narrate/합성 데이터가 `ORA-20000`으로 실패 — 데모 전 상태 점검 필요 (p174–175).
4. LLM 환각으로 SQL 생성·실행이 실패할 수 있음(가이드 공식 경고, p14·p45). 데모 UI에 오류 표시와 재시도 UX를 마련할 것.
5. `feedback`은 26ai 전용 + NL2SQL 프로파일 전용(RAG 프로파일 불가), 마지막 AI SQL 참조 시 `SYS.V_$MAPPED_SQL`/`V_$SESSION` READ 권한 필요 (p63–64).
