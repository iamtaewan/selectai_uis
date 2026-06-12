# PRD — Select AI Demo Studio

| 항목 | 내용 |
|---|---|
| 제품명 | Select AI Demo Studio |
| 버전 | PRD v1.0 (2026-06-12) |
| 작성자 | 시니어 프로덕트 매니저 (전문가 2/8) |
| 기술 근거 | `docs/research/selectai-reference.md` (Oracle AI Database Select AI User's Guide, Release 26ai, G35918-05) |
| 관련 문서 | `docs/architecture.md` (기술 상세), `docs/research/selectai-reference.md` (도메인 레퍼런스) |

---

## 1. 개요

### 1.1 배경

Oracle Autonomous AI Database 26ai의 **Select AI**는 자연어를 SQL로 변환(NL2SQL)하고, 데이터 기반 대화·요약·번역까지 제공하는 차별화 기능이다. 그러나 고객 앞에서 이 기능을 시연하려면 `DBMS_CLOUD_AI` 패키지, 프로파일 속성 JSON, 권한/ACL 설정, wallet 기반 접속 등 상당한 DBA·PL/SQL 지식이 필요하다.

### 1.2 문제 정의 — Presales가 Select AI를 시연하기 어려운 이유

1. **준비 단계가 길고 오류에 취약**: wallet 다운로드 → 접속 구성 → `GRANT EXECUTE ON DBMS_CLOUD_AI` → (외부 공급자 시) 네트워크 ACL → credential 생성 → `CREATE_PROFILE`까지 수작업 SQL이 최소 6단계. 한 단계라도 빠지면 데모 현장에서 `ORA-` 오류가 발생한다.
2. **세션 상태 함정**: `SET_PROFILE`/`SET_CONVERSATION_ID`는 세션 단위라 SQL 도구를 바꾸거나 재접속하면 사라진다. Database Actions/APEX에서는 `SELECT AI` 키워드 자체가 미지원이다 (레퍼런스 §1).
3. **프로파일 속성의 학습 장벽**: `comments`, `object_list_mode`, `enforce_object_list`, `oci_apiformat` 등 20개 이상의 속성 의미를 영어 매뉴얼에서 찾아야 한다.
4. **"왜 정확해지는가"를 보여주기 어려움**: COMMENT 기반 메타데이터 증강의 효과는 전/후 비교가 핵심인데, 수작업으로는 두 프로파일을 오가며 시연하기 번거롭다.
5. **재현성 부족**: 데모마다 환경을 새로 구성하므로 영업 대표나 파트너처럼 기술력이 낮은 인력은 사실상 시연이 불가능하다.

### 1.3 제품 비전

> **"클릭 몇 번으로, SQL 한 줄 직접 작성하지 않고, 15분 안에 Select AI의 가치를 고객에게 보여준다."**

Select AI Demo Studio는 wallet zip 업로드부터 권한 점검, 프로파일 생성, 액션 시연, 챗봇, 메타데이터 증강 전/후 비교까지를 **가이드된 웹 UI**로 제공한다. 모든 화면에 한국어 해설을 붙여 데모 도구이자 **학습 도구**로 기능한다.

---

## 2. 목표 및 비목표

### 2.1 목표

| # | 목표 | 측정 |
|---|---|---|
| G1 | 비개발자도 데모 가능한 수준의 가이드 UI 제공 | 영업 대표 페르소나가 매뉴얼 없이 데모 완주 |
| G2 | 데모 환경 준비 시간을 수작업 대비 대폭 단축 | 신규 DB 연결~첫 NL2SQL 응답 15분 이내 |
| G3 | Select AI 핵심 가치(NL2SQL, 대화, 메타데이터 증강) 시연 커버 | FR-06/07/08 수용 기준 충족 |
| G4 | 프로파일 속성의 한국어 해설로 학습 효과 제공 | 레퍼런스 §3의 21개 검증 속성 전부 해설 표시 |
| G5 | 데모 중 오류 발생 시 원인과 조치를 화면에서 안내 | 주요 ORA 오류(ORA-00923, ORA-20000 등) 친화적 메시지 매핑 |

### 2.2 비목표 (Non-goals)

- **프로덕션급 보안**: 사내 데모 도구다. 다만 wallet/비밀번호는 서버 측 암호화 저장하고 로그에 남기지 않는다(최소선). SSO, 감사 로그, 비밀 관리 서비스 연동은 범위 외. **암호화 키 회전·OCI Vault 연동도 비목표** — 단일 시연자가 단기간 사용하는 도구이므로 도입하지 않는다 (로컬 `secret.key` + Fernet 최소선으로 충분).
- **멀티테넌시 / 다중 사용자 동시성**: 단일 시연자 사용 가정. 사용자 계정 체계 없음.
- **admin 외 DB 사용자 지원**: DB 사용자는 `admin` 고정 (확정 사항). 일반 사용자용 grant 위저드는 "시연용 기능"으로만 제공.
- **Select AI Agent (Part II)**: `agent` 액션 및 `DBMS_CLOUD_AI_AGENT` 패키지는 범위 외 (P2 후보로만 기록).
- **RAG/Vector Index 전체 구현**: 벡터 인덱스 생성·파이프라인은 v1 범위 외 (P2).
- **데모 데이터셋 일반화**: 임의 고객 스키마 자동 분석은 비목표. SH/무비 데모 스키마 중심.
- **다국어 UI**: UI 언어는 한국어 단일.
- **온프레미스 DB 지원**: OCI Autonomous Database 26ai 전용.

---

## 3. 사용자 페르소나

### P1. 박선영 — Presales 솔루션 엔지니어 (주 사용자)

- **기술 수준**: 상. SQL/PL/SQL 능숙, OCI 콘솔 익숙. 그러나 데모마다 환경을 새로 꾸미는 반복 작업이 고통.
- **데모 시나리오**: 고객 PoC 미팅에서 고객 유사 스키마로 NL2SQL 정확도와 `comments` 증강 효과를 깊이 있게 시연. `showsql`/`explainsql`/`showprompt`로 내부 동작까지 설명.
- **필요**: 빠른 환경 재현(커넥션/프로파일 저장·재사용), 생성 SQL 원문 표시, 속성 미세 조정(temperature, model, enforce_object_list), 오류 시 원인 진단.

### P2. 김재현 — 영업 대표 (Account Executive)

- **기술 수준**: 하. SQL 미작성. 브라우저 기반 도구만 사용 가능.
- **데모 시나리오**: 고객 임원 미팅에서 Presales가 미리 구성해둔 커넥션·프로파일을 선택하고, 챗봇 화면에서 준비된 자연어 질문 몇 개를 실행해 "말로 데이터를 묻는다"는 가치를 5분 내 전달.
- **필요**: 사전 구성된 환경 원클릭 로드, 추천 질문(canned prompts) 버튼, 기술 용어 없는 화면, 실패 시 "다시 시도" 단순 UX.

### P3. 이민호 — 파트너 SI 엔지니어

- **기술 수준**: 중. Java/Python 개발 가능, Oracle DB 운영 경험은 얕음. Select AI는 처음.
- **데모 시나리오**: 파트너사 자체 고객 대상 시연 + 본인 학습. 각 화면의 한국어 해설(속성 설명, 권한 SQL 미리보기, 실행된 실제 PL/SQL 표시)을 통해 Select AI 구조를 익히고, 이후 자사 솔루션에 통합을 검토.
- **필요**: "이 버튼이 실제로 실행하는 SQL" 투명하게 노출, 속성별 한국어 설명과 문서 페이지 근거, 권한 점검의 통과/실패 사유 상세.

---

## 4. 핵심 기능 요구사항

> 우선순위: **P0** = MVP 필수, **P1** = v1.1, **P2** = 향후.
> 모든 Select AI 기술 사실은 `docs/research/selectai-reference.md` 기준.

### FR-01. 데이터베이스 연결 (Wallet 업로드 + admin 접속) — **P0**

**설명**: mTLS wallet zip 파일을 업로드하고 `admin` 사용자 비밀번호와 서비스 레벨(예: `_high`/`_medium`/`_low` TNS alias)을 입력하면 python-oracledb로 ADB 26ai에 접속한다. wallet이 없는 경우 **OCI CLI를 통해 지정 컴파트먼트(기본: TAEWAN.KIM)·ADB 표시 이름으로 wallet을 자동 다운로드**하는 하위 기능을 제공한다 (저장 위치 `~/.selectai/wallets/` — 상세는 architecture.md §3.1.1).

**수용 기준**:
- [ ] wallet zip 업로드 시 서버가 압축 해제·검증하고 `tnsnames.ora`의 TNS alias 목록을 자동 추출해 선택지로 제시한다.
- [ ] wallet이 없으면 "자동 다운로드" 경로에서 ADB 표시 이름·wallet 암호 입력만으로 OCI CLI가 wallet을 내려받아 업로드와 동일한 alias 선택 단계로 합류한다 (컴파트먼트 기본값 TAEWAN.KIM, 변경 가능).
- [ ] OCI CLI 미설치/인증 실패 시 한국어 안내와 함께 수동 업로드 경로로 폴백을 유도한다.
- [ ] 잘못된 zip(비밀번호 불일치, 파일 누락) 시 한국어 오류 메시지와 해결 방법을 표시한다.
- [ ] 접속 성공 시 DB 버전·인스턴스명·현재 사용자를 표시한다.
- [ ] 비밀번호(wallet 암호 포함)는 평문 로그/응답에 노출되지 않는다.

### FR-02. 커넥션 관리 (저장/목록/테스트/삭제) — **P0**

**설명**: 검증된 커넥션을 이름 붙여 저장하고, 목록 조회·연결 테스트·삭제를 제공한다. 영업 대표(P2)가 "저장된 커넥션 선택"만으로 데모를 시작할 수 있게 한다.

**수용 기준**:
- [ ] 커넥션 CRUD: 저장(별칭, wallet, 비밀번호), 목록, 삭제.
- [ ] "테스트" 버튼이 5초 내 성공/실패와 실패 사유를 반환한다 (타임아웃 처리 포함).
- [ ] 저장된 자격 정보는 서버 측에 암호화되어 저장된다.
- [ ] 마지막 사용 커넥션이 다음 실행 시 기본 선택된다.

### FR-03. 권한 사전 점검 및 자동 적용 — **P0**

**설명**: Select AI 사전 요구 사항을 체크리스트로 점검하고, 미충족 항목을 원클릭으로 적용한다. 레퍼런스 §4 기준:

- EXECUTE 점검: `DBA_TAB_PRIVS`에서 `DBMS_CLOUD_AI`(필수), `DBMS_CLOUD_PIPELINE`(RAG 시) 확인 → 미충족 시 `GRANT EXECUTE ON DBMS_CLOUD_AI TO <user>` 적용.
- 네트워크 ACL: **OCI Generative AI는 ACL 불필요 (p34)** — 기본 공급자(OCI)에서는 "필요 없음(통과)"으로 표시하고, 외부 공급자(openai/cohere/azure/google/anthropic/aws) 선택 시에만 `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE`를 공급자별 host로 적용. Hugging Face는 provider 문자열이 본 PDF에서 확정되지 않았으므로 P0 공급자 enum에서 제외하고, 필요한 경우 "고급 JSON 직접 입력"으로 우회한다.
- 자격증명: `DBMS_CLOUD.CREATE_CREDENTIAL`(OCI API 서명 키 방식: user_ocid/tenancy_ocid/private_key/fingerprint) 또는 Resource Principal — `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI')` 후 `OCI$RESOURCE_PRINCIPAL` 사용. (주의: `ENABLE_RESOURCE_PRINCIPAL`이라는 프로시저명은 26ai 가이드에 없음)
- Feedback용: `GRANT READ ON SYS.V_$MAPPED_SQL / SYS.V_$SESSION` (P1, FR-06 feedback 연동).
- Data Access 상태: `DISABLE_DATA_ACCESS` 상태이면 `narrate`·합성 데이터가 `ORA-20000`으로 실패하므로, 점검 항목에 **데이터 액세스 활성 여부**를 포함하고 `ENABLE_DATA_ACCESS` 원클릭 복구를 제공.

**수용 기준**:
- [ ] 점검 결과가 항목별 통과/실패/해당없음으로 표시되고, 각 항목에 근거 SQL과 한국어 설명이 붙는다.
- [ ] "적용" 클릭 전 실행될 SQL 전문을 미리보기로 보여준다 (P3 페르소나 학습 효과).
- [ ] OCI GenAI 공급자에서는 ACL 항목이 "필요 없음"으로 자동 처리된다.
- [ ] 적용 후 자동 재점검으로 전 항목 통과를 확인한다.

### FR-04. 프로파일 설정 — 속성별 한국어 해설 — **P0**

**설명**: `DBMS_CLOUD_AI.CREATE_PROFILE`의 attributes JSON을 폼 UI로 구성한다. 레퍼런스 §3에서 검증된 21개 속성(`provider`, `credential_name`, `object_list`, `object_list_mode`, `comments`, `annotations`, `constraints`, `conversation`, `temperature`, `max_tokens`, `model`, `region`, `oci_compartment_id`, `oci_apiformat`, `oci_endpoint_id`, `enforce_object_list`, `case_sensitive_values`, `target_language`, `vector_index_name`, `azure_resource_name`/`azure_deployment_name`, `provider_endpoint`) 각각에 한국어 해설(레퍼런스의 해설 문구 사용)과 근거 페이지를 툴팁/패널로 표시한다.

**대상 테이블 선택 (핵심)**: 프로파일의 `object_list`(NL2SQL 대상 객체)는 **인증한 커넥션 사용자가 DB에서 볼 수 있는 테이블 중 사용자가 직접 선택**해 구성한다. 앱이 제공하는 SH·무비 모호 스키마는 데모 편의용 프리셋일 뿐이며(X3 결정), 사용자는 자신이 접속한 스키마의 임의 테이블을 대상으로 골라 프로파일을 만들 수 있어 고객 자신의 데이터로 즉석 시연이 가능하다.

**기본값 (확정)**: `provider: "oci"`, `model: "meta.llama-3.3-70b-instruct"` (OCI GenAI 기본 모델), `oci_compartment_id`는 TAEWAN.KIM 컴파트먼트 OCID, `region: "us-chicago-1"`.

**수용 기준**:
- [ ] 21개 검증 속성 전부에 한국어 해설이 표시된다.
- [ ] `object_list`는 **인증한 커넥션 사용자가 DB에서 볼 수 있는** 스키마/테이블만 노출하는 브라우저(`ALL_*` 뷰 기반)에서 체크박스로 선택해 구성한다. 스키마 선택기는 인증 사용자 자신의 스키마를 기본 선택하며, 접근 가능한 다른 스키마(SH 등)로 전환·혼합 선택할 수 있다. JSON 직접 입력도 허용한다.
- [ ] 테이블을 아무것도 선택하지 않으면 `object_list`를 생략하여 "현재 스키마 전체 자동 선택"이 적용되고, 선택한 테이블이 그대로 생성되는 프로파일의 대상 객체가 된다.
- [ ] 폼 입력으로부터 생성될 `CREATE_PROFILE` PL/SQL 전문을 미리보기로 표시한다.
- [ ] OCI 모델 선택지는 레퍼런스 §5의 Chat 모델 목록(meta.llama 계열, cohere.command-r 계열, xai.grok-3/4 계열)을 제공한다.
- [ ] 외부 공급자 선택 시 FR-03 ACL 항목과 연동해 경고를 표시한다.

### FR-05. 프로파일 관리 (CRUD + 기본 프로파일) — **P0**

**설명**: `USER/DBA_CLOUD_AI_PROFILES` 뷰 기반 목록, `USER/DBA_CLOUD_AI_PROFILE_ATTRIBUTES` 기반 속성 상세 조회, `SET_ATTRIBUTE(S)` 기반 수정, `DROP_PROFILE` 삭제, 그리고 **앱 수준의 "기본 프로파일"** 지정을 제공한다.

> 설계 결정: `SET_PROFILE`은 세션 상태이므로(stateless 백엔드에서 무효) "기본 프로파일"은 DB가 아닌 **앱 설정으로 저장**하고, 모든 실행 시 `GENERATE(profile_name => ...)`에 명시 전달한다.

**수용 기준**:
- [ ] 프로파일 목록에 이름·공급자·모델·상태가 표시된다.
- [ ] 속성 상세 화면이 `*_CLOUD_AI_PROFILE_ATTRIBUTES` 뷰 값을 한국어 해설과 함께 표시한다 ("showparameter" 대체 — 해당 액션은 존재하지 않음).
- [ ] 수정 시 `SET_ATTRIBUTE`/`SET_ATTRIBUTES` 호출 SQL을 미리보기로 표시한다.
- [ ] 기본 프로파일이 액션 시연/챗봇 화면에 자동 적용된다.
- [ ] `ENABLE_PROFILE`/`DISABLE_PROFILE` 토글을 제공한다 (P1).

### FR-06. Select AI 액션 시연 — **P0 (핵심) / 일부 P1**

**설명**: 자연어 프롬프트 1개를 입력하면 선택한 액션으로 실행한다. 백엔드는 stateless이므로 `SELECT AI` 키워드가 아닌 **`DBMS_CLOUD_AI.GENERATE(prompt, profile_name, action, params)`** 를 표준 호출 패턴으로 사용한다 (레퍼런스 §1, p42·p44).

**액션 목록 (확정 — 레퍼런스 ch8 공식 표)**:

| 액션 | 우선순위 | 데모 표시 |
|---|---|---|
| `runsql` | P0 | 생성 SQL 실행 결과를 표(grid)로 표시 (기본 액션) |
| `showsql` | P0 | 생성 SQL만 구문 강조 표시 (실행 안 함) |
| `explainsql` | P0 | 생성 SQL + LLM의 자연어 설명 |
| `narrate` | P0 | 실행 결과의 자연어 서술 (DISABLE_DATA_ACCESS 시 ORA-20000 안내) |
| `chat` | P0 | LLM 직접 대화 (pass-through) |
| `showprompt` | P1 | LLM에 전송되는 증강 프롬프트 원문 — "내부 들여다보기" 시연. **`showparameter`라는 액션은 존재하지 않으며 UI에 사용 금지** |
| `feedback` | P1 | 생성 SQL에 긍정/부정 피드백 → 정확도 개선 (26ai 전용, NL2SQL 프로파일 전용, V_$MAPPED_SQL/V_$SESSION READ 필요) |
| `summarize` | P2 | 텍스트 요약 (`DBMS_CLOUD_AI.SUMMARIZE`) |
| `translate` | P2 | OCI 번역 (provider oci 전용, `target_language` 필요) |
| `agent` | 범위 외 | Select AI Agent — 비목표 |

**수용 기준**:
- [ ] P0 5개 액션(runsql/showsql/explainsql/narrate/chat)이 동일 프롬프트에 대해 탭/토글로 전환 실행된다.
- [ ] 모든 실행에서 실제 호출된 `GENERATE` SQL 전문을 펼침 영역으로 노출한다.
- [ ] SH 스키마 기반 추천 프롬프트 버튼 제공 (예: "how many customers exist", "how many customers in San Francisco are married" — 레퍼런스 §9).
- [ ] LLM 환각/SQL 실패 시(가이드 공식 경고 p14·p45) 오류 원문 + 한국어 해설 + 재시도 버튼을 표시한다.
- [ ] 프롬프트 내 작은따옴표는 백엔드가 자동 이스케이프한다 (`''`).
- [ ] 응답 시간(latency)을 함께 표시한다.
- [ ] **SQL 로그 터미널 (전 화면 공통)**: DB Interaction이 발생하는 모든 화면 하단에 API 응답의 `executed_sql`/`elapsed_ms`를 시계열로 누적 표시하는 VS Code 터미널 스타일 도킹 패널을 제공하고, show/no show 토글(상태바 클릭 + Ctrl/Cmd+`)을 지원한다. 인라인 SQL 펼침(SQL 투명 모드)과 독립 동작 — 상세는 design.md §1.3.

### FR-07. 챗봇 통합 시연 (Select AI Conversations) — **P0**

**설명**: 멀티턴 대화형 챗봇 UI. `DBMS_CLOUD_AI.CREATE_CONVERSATION` 함수로 conversation_id(UUID)를 발급받고, 매 턴 `GENERATE(prompt, profile_name, action, params => '{"conversation_id":"<uuid>"}')`로 호출한다 (stateless 표준 패턴, 레퍼런스 §6). `SET_CONVERSATION_ID`는 세션 상태이므로 사용하지 않는다.

**수용 기준**:
- [ ] 새 대화 생성 시 `title`/`description`/`retention_days`/`conversation_length` 설정 가능 (기본값 제공).
- [ ] 대화가 지원하는 액션(`runsql`, `showsql`, `explainsql`, `narrate`, `chat` — p47 Note)을 턴마다 선택할 수 있다 (기본 `narrate` 또는 `chat`).
- [ ] 멀티턴 맥락 시연: "what are the total number of customers" → "break out count of customers by country" 류의 후속 질문이 이전 맥락을 유지한다.
- [ ] **맥락 비교 시연**: 동일 질문을 conversation_id 없이/있이 실행해 응답 차이를 나란히 보여주는 모드 제공 (p132 근거).
- [ ] 대화 목록(`USER_CLOUD_AI_CONVERSATIONS`)과 턴 이력(`USER_CLOUD_AI_CONVERSATION_PROMPTS`)을 조회·삭제(`DROP_CONVERSATION`)할 수 있다.

### FR-08. Comment/Annotation 메타데이터 증강 전/후 비교 — **P0 (차별화 핵심)**

**설명**: NL2SQL 정확도에 대한 메타데이터 증강 효과를 한 화면에서 비교 시연한다 (레퍼런스 §7, ch19 p147–150 방식).

플로우: ① 모호한 컬럼명(c1, c2, … c7)을 가진 데모 무비 테이블을 원클릭 생성 → ② `comments: "false"` 프로파일로 질문("what are our total views") 실행, 잘못된 SQL 확인 → ③ UI에서 테이블/컬럼 COMMENT 입력·적용(`COMMENT ON TABLE/COLUMN`) → ④ `comments: "true"` 프로파일로 동일 질문 재실행 → ⑤ 생성 SQL과 결과를 **좌우 분할 비교**로 표시.

**수용 기준**:
- [ ] 데모용 모호 스키마(레퍼런스 §9 무비 테이블 패턴)를 생성/초기화하는 원클릭 셋업 제공.
- [ ] 테이블/컬럼 COMMENT를 UI 폼으로 조회·작성·적용할 수 있다 (실행 DDL 미리보기 포함).
- [ ] 전(comments off)/후(comments on) 프로파일 쌍을 자동 생성·전환한다.
- [ ] 동일 프롬프트의 전/후 생성 SQL과 실행 결과를 나란히 비교 표시한다.
- [ ] (P1) `annotations: "true"`, `constraints: "true"` 증강 시연 확장.
- [ ] (P1) `showprompt`로 증강 프롬프트에 COMMENT가 포함되는 것을 직접 확인하는 보조 화면.

### FR-09 (보조). 데모 상태 대시보드 — **P1**

**설명**: 데모 시작 전 환경 건강 점검 요약 — 커넥션 상태, 권한 점검 결과, Data Access 활성 여부(ORA-20000 예방), 기본 프로파일 유효성, 데모 스키마 존재 여부를 한 화면에 신호등으로 표시. 영업 대표(P2)의 "데모 가능 여부" 한눈 확인용.

### FR-10. 데모 환경 정리 (Cleanup + 생성 리소스 대장) — **P0**

**설명**: 앱이 생성한 프로파일, credential, 네트워크 ACL, 대화, 데모 테이블, 시연용 grant, 커넥션/wallet 메타데이터를 `~/.selectai/resources.json`의 **생성 리소스 대장(ledger)** 에 기록하고, 데모 종료 시 PG-08 설정 화면에서 원클릭 정리를 제공한다. 고객 환경에서 `admin` 계정으로 시연하는 도구이므로 흔적 제거는 MVP 필수 기능이다.

**수용 기준**:
- [ ] 앱이 생성·변경한 리소스는 `resource_type`, `resource_name`, `owner`, `create_sql`, `cleanup_sql`, `created_at`, `cleanup_status`를 포함해 로컬 ledger(`~/.selectai/resources.json`)에 기록된다.
- [ ] PG-08 "데모 환경 정리" 버튼이 정리 대상 목록과 실행될 SQL/파일 삭제 작업을 먼저 보여준다.
- [ ] `GET /api/v1/resources`는 정리 대상 목록을, `DELETE /api/v1/resources/{id}`는 개별 정리를, `POST /api/v1/resources/cleanup`은 선택 대상 일괄 정리 후 결과를 반환한다.
- [ ] 실패한 정리 항목은 실패 사유를 남기고, 나머지 항목 정리는 계속한다.
- [ ] 정리 후 대시보드와 설정 화면에서 남은 리소스 수를 다시 표시한다.

---

## 5. 사용자 여정 (핵심 데모 플로우)

```
[1] 연결          wallet zip 업로드(또는 OCI CLI 자동 다운로드) → admin 비밀번호 → TNS alias 선택
      ↓            → 접속 성공 → 커넥션 저장
      ↓
[2] 권한 점검      체크리스트 자동 실행 (EXECUTE / credential·Resource Principal / Data Access 상태
      ↓            / 외부 공급자 시 ACL) → 미충족 항목 원클릭 적용 → 전 항목 녹색
[3] 프로파일 생성   공급자(기본 OCI GenAI) → 모델(기본 meta.llama-3.3-70b-instruct) → object_list
      ↓            체크박스 선택 → 속성 한국어 해설 확인 → PL/SQL 미리보기 → 생성 → 기본 프로파일 지정
[4] 자연어 쿼리     추천 프롬프트 클릭 → runsql 결과 표 확인 → showsql/explainsql/narrate 탭 전환으로
      ↓            동일 질문의 다른 액션 비교 → 실행된 GENERATE SQL 펼쳐 보기
[5] 챗봇           새 대화 생성 → 멀티턴 질문 ("total customers" → "break out by country" →
      ↓            "top 5 with rank") → 맥락 유지 확인 → (옵션) 대화 없음 vs 있음 비교
[6] 증강 비교       모호 스키마 원클릭 생성 → comments off로 오답 SQL 확인 → COMMENT 입력·적용 →
      ↓            comments on으로 재실행 → 좌우 비교로 정확도 개선 입증
[데모 완료]        전체 소요 목표: 신규 환경 기준 15분, 저장된 환경 재사용 기준 3분
```

이탈 지점 대응: 각 단계 실패 시 다음 단계 진입을 막고(가드), 실패 원인과 조치 버튼을 해당 화면에서 제공한다.

---

## 6. 기술 요구사항 요약

> 상세 설계는 `docs/architecture.md`에 위임. 아래는 PRD 수준의 확정 사항만 기재.

| 항목 | 확정 내용 |
|---|---|
| 프론트엔드 | React |
| 백엔드 | Python FastAPI + python-oracledb |
| DB | OCI Autonomous Database 26ai, 사용자 `admin` |
| DB 연결 | mTLS wallet zip 업로드 |
| AI 공급자 기본값 | OCI Generative AI (기본 모델 `meta.llama-3.3-70b-instruct`) |
| 호출 패턴 (필수) | stateless 원칙 — `SELECT AI` 키워드·`SET_PROFILE`·`SET_CONVERSATION_ID` 대신 `DBMS_CLOUD_AI.GENERATE(prompt, profile_name, action, params)` 사용 |
| OCI 컴파트먼트 | `TAEWAN.KIM` / `ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq` — 모든 OCI 리소스 및 프로파일 `oci_compartment_id` 기본값 |
| 배포 | 로컬 개발 → OCI Compute 배포 |
| 기술 근거 | 모든 Select AI API/속성/권한은 `docs/research/selectai-reference.md`만을 근거로 구현 (추측 금지) |

---

## 7. 성공 지표

| 지표 | 정의 | 목표 |
|---|---|---|
| 데모 준비 시간 (신규) | 신규 wallet 업로드 → 첫 NL2SQL 응답 | ≤ 15분 |
| 데모 준비 시간 (재사용) | 저장된 커넥션·프로파일 로드 → 첫 응답 | ≤ 3분 |
| 시연 클릭 수 | 핵심 플로우(여정 1~6) 완주에 필요한 사용자 입력 | ≤ 30회 |
| 수작업 SQL 작성 수 | 데모 완주에 사용자가 직접 작성한 SQL 문 | 0건 |
| 비개발자 완주율 | P2 페르소나 테스트에서 매뉴얼 없이 챗봇 시연 완료 비율 | ≥ 80% |
| 오류 자가 복구율 | 오류 발생 시 화면 안내만으로 해결된 비율 | ≥ 70% |
| 학습 효과 | 프로파일 속성 한국어 해설 커버리지 (검증 21개 속성 기준) | 100% |

---

## 8. 릴리스 계획

### MVP — P0 (1차 릴리스)

- FR-01 연결, FR-02 커넥션 관리, FR-03 권한 점검/적용
- FR-04 프로파일 설정(한국어 해설), FR-05 프로파일 관리
- FR-06 액션 5종 (runsql, showsql, explainsql, narrate, chat)
- FR-07 챗봇 (Conversations 기반)
- FR-08 Comment 증강 전/후 비교
- FR-10 데모 환경 정리 및 생성 리소스 대장

### v1.1 — P1

- FR-06 확장: `showprompt`, `feedback` (+V_$MAPPED_SQL/V_$SESSION grant 점검 연동)
- FR-08 확장: annotations/constraints 증강, showprompt 연계 확인 화면
- FR-05 확장: ENABLE/DISABLE_PROFILE 토글
- FR-09 데모 상태 대시보드
- Data Access ON/OFF 거버넌스 시연 (ENABLE/DISABLE_DATA_ACCESS)

### 향후 — P2

- `summarize`, `translate` 액션 (translate는 OCI Language IAM 정책 필요)
- `object_list_mode: "automated"` 시연 (26ai 자동 객체 선별)
- 합성 데이터 생성 (`GENERATE_SYNTHETIC_DATA`) — 데모 스키마 채우기 자동화
- RAG / Vector Index (`DBMS_CLOUD_PIPELINE` 권한 + 테이블스페이스 쿼터 점검 포함)
- (검토만) Select AI Agent

---

## 9. 리스크 및 오픈 이슈

### 리스크

| # | 리스크 | 영향 | 완화 |
|---|---|---|---|
| R1 | LLM 환각으로 생성 SQL 실패 — 가이드 공식 경고 (p14·p45) | 데모 현장 신뢰도 하락 | 오류 친화 표시 + 재시도 UX(FR-06), 추천 프롬프트는 검증된 SH 예제 사용 |
| R2 | `DISABLE_DATA_ACCESS` 상태에서 narrate가 ORA-20000으로 실패 | 챗봇/narrate 데모 중단 | FR-03 점검 항목 포함 + FR-09 대시보드 신호등 |
| R3 | 세션 상태(SET_PROFILE 등) 의존 코드 혼입 | 커넥션 풀에서 간헐적 오동작 | GENERATE 패턴을 아키텍처 원칙으로 강제 (§6), 코드 리뷰 체크 항목화 |
| R4 | 프로파일 속성 전체 표가 본 가이드에 없음 (Supplied Package Reference 참조) | 미검증 속성 노출 시 오류 | UI는 검증 21개 속성만 제공, 그 외는 "고급 JSON 직접 입력"으로 격리 |
| R5 | admin 자격/ wallet의 평문 유출 | 보안 사고 | 서버 측 암호화 저장, 로그 마스킹 (비목표인 프로덕션 보안과 별개의 최소선) |
| R6 | OCI GenAI 리전/모델 가용성 변화 (deprecated 모델 존재) | 프로파일 생성 실패 | 모델 목록에 deprecated 표기, 기본값은 `meta.llama-3.3-70b-instruct` 유지 |
| R7 | feedback 액션의 추가 grant(V_$MAPPED_SQL/V_$SESSION) 누락 | P1 기능 실패 | FR-03 점검 항목에 P1 시점 추가 |

### 오픈 이슈

| # | 이슈 | 담당(권장) | 기한 |
|---|---|---|---|
| O1 | **결정 완료**: UI 기본값은 Resource Principal(`ENABLE_PRINCIPAL_AUTH(provider=>'OCI')` + `OCI$RESOURCE_PRINCIPAL`), API 서명 키 방식 폴백 제공. 두 방식 모두 폼 지원 (architecture.md §6.4) | 아키텍트 | 완료 |
| O2 | **결정 완료**: 커넥션 자격은 `~/.selectai/connections.json`에 Fernet 암호화 저장(키는 `secret.key`/`APP_SECRET_KEY`), wallet은 `~/.selectai/wallets/`에 파일 보관. SQLite 미사용 — JSON 파일 저장소로 통일 | 아키텍트/백엔드 | 완료 |
| O3 | **결정 완료**: P0이 시드/검증해 제공하는 데모 프리셋은 SH(존재 점검)와 무비 모호 스키마 2종뿐이다. 단 대상 테이블은 프리셋에 한정되지 않으며, 사용자는 인증 스키마에서 보이는 임의 테이블을 `object_list`로 선택할 수 있다(FR-04). 한국형 `SALES_DEMO`는 PDF 근거 없는 자체 설계이므로 P1 프리셋으로 보류 | PM/백엔드 | 완료 |
| O4 | **결정 완료**: 새 conversation 기본 `retention_days=7`, 데모 종료 시 자동 삭제 없음. PG-08 Cleanup에서 수동 일괄 삭제 | PM/백엔드 | 완료 |
| O5 | **결정 완료**: 단일 OCI Compute VM + nginx(리버스 프록시/TLS 종단) + systemd 관리 uvicorn(루프백 바인딩), 443만 개방, Docker 미채택 (architecture.md §6.2) | 아키텍트 | 완료 (실배포 시 적용) |
