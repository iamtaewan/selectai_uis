# 문서 인덱스 (INDEX.md) — Select AI Demo Studio

| 항목 | 내용 |
|---|---|
| 문서 | docs/INDEX.md v1.0 (2026-06-12) |
| 작성자 | 시니어 프로덕트 매니저 (전문가 2/8, 최종 교차 검토) |
| 목적 | 전체 문서 맵 — 각 문서의 목적·대상 독자·읽는 순서 가이드 |

---

## 1. 프로젝트 개요

**Select AI Demo Studio**: Oracle Autonomous AI Database 26ai의 Select AI(NL2SQL)를 오라클 Presales/영업/파트너가 클릭만으로 시연할 수 있게 하는 데모 웹 애플리케이션.

- 스택(확정): React 프론트엔드 + Python FastAPI 백엔드 (python-oracledb thin, mTLS wallet zip 업로드 또는 OCI CLI 자동 다운로드 — FR-01 하위 기능)
- AI 공급자 기본값(확정): OCI Generative AI (`meta.llama-3.3-70b-instruct`, `us-chicago-1`)
- OCI 컴파트먼트(필수): `TAEWAN.KIM` / `ocid1.compartment.oc1..<your-compartment-ocid>`
- 핵심 아키텍처 원칙: 모든 Select AI 실행은 stateless한 `DBMS_CLOUD_AI.GENERATE(prompt, profile_name, action, params)` 단일 패턴 (`SELECT AI` 키워드·`SET_PROFILE`·`SET_CONVERSATION_ID` 사용 금지)

---

## 2. 문서 맵

| # | 문서 | 목적 | 주 대상 독자 | 비고 |
|---|---|---|---|---|
| 1 | [`docs/research/selectai-reference.md`](research/selectai-reference.md) | **모든 기술 사실의 단일 근거 문서.** Select AI 액션 목록(ch8 공식 표), `DBMS_CLOUD_AI` 프로시저/함수, 검증 21개 프로파일 속성과 한국어 해설, 사전 요구 권한 SQL, Conversations, Comment 증강 패턴, 권장 데모 스키마. Oracle Select AI User's Guide 26ai (G35918-05) 기반 | 전원 (기술 사실 확인 시 필수) | 액션명·프로시저명·속성명·권한은 **이 문서 외 출처로 추측 금지** |
| 2 | [`PRD.md`](../PRD.md) | 제품 요구사항 정의: 문제/비전, 목표·비목표, 페르소나(P1 Presales / P2 영업 / P3 파트너), 기능 요구사항 **FR-01~FR-10**, 사용자 여정, 성공 지표, 릴리스 계획(P0/P1/P2), 리스크(R1~R7)·오픈 이슈(O1~O5) | PM, 전 직군 | 기능 ID(FR-xx)·리스크 ID(R-x)·이슈 ID(O-x)의 원천 |
| 3 | [`docs/architecture.md`](architecture.md) | 기술 설계: 시스템 구성도, 디렉토리/레이어 구조, wallet·커넥션 풀 전략, GENERATE 단일 호출 패턴 결정, 챗봇 상태 관리, 배포(OCI Compute, nginx+systemd), 환경변수, **오픈 이슈 O1~O5 결정** | 백엔드/프론트 개발자, 아키텍트 | API 경로의 상세 계약은 api-spec.md가 기준 |
| 4 | [`design.md`](../design.md) | UX 설계: 페이지 목록(PG-00~PG-08)과 경로, 내비게이션/가드 레일, 페이지별 레이아웃·상태(빈/로딩/오류/정상)·인터랙션, 단순/전문가 모드, 설계 전제 1~5 | 프론트 개발자, 디자이너 | 페이지 ↔ FR ↔ API 매핑의 UI 측 기준 |
| 5 | [`style.md`](../style.md) | 비주얼 스타일 가이드: Oracle Redwood 룩앤필 재현 — 컬러/타이포/스페이싱 CSS 토큰, 10종 공용 컴포넌트 스타일 명세, 라이트 모드 단일 결정, 구현 가이드(Tailwind v4, Radix, Shiki 등) | 프론트 개발자, 디자이너 | `src/styles/tokens.css`의 원본 명세 |
| 6 | [`docs/api-spec.md`](api-spec.md) | **백엔드 API 계약의 단일 소스**: 42개 엔드포인트 전체 명세(`/api/v1`, `X-Connection-Id` 헤더, wallet 자동 다운로드 §2.7, Resources CRUD §10 포함), 공통 응답 envelope(`data`/`executed_sql`/`elapsed_ms`), ORA 오류→한국어 매핑, Pydantic v2 모델, 타임아웃/동시성 전략 | 백엔드/프론트 개발자 | runsql 2단계 실행, 검증 21개 속성 메타 포함 |
| 7 | [`docs/security.md`](security.md) | 보안 설계: 위협 모델(A1~A5), 자격증명 암호화·마스킹, LLM 생성 SQL 읽기 전용 게이트, Data Access·object_list 통제, 네트워크 최소 개방, **데모 후 정리 체크리스트**, 구현 체크리스트 S1~S11 | 백엔드 개발자, 시연자(정리 체크리스트) | "데모 도구지만 고객 환경에서 사고 금지"의 최소선 |
| 8 | [`docs/demo-scenarios.md`](demo-scenarios.md) | 데모 운영 가이드: 표준 20분/단축 5분 시나리오(타임라인·멘트), 샘플 데이터셋 방침, 자연어 질문 라이브러리(액션별/증강 비교용), 리허설 체크리스트(D-1/D-0), 오류 즉석 대처법, QA 테스트 계획(QA-01~10, E2E) | 시연자(P1/P2/P3), QA | 데모 직전엔 §5 리허설 체크리스트만 봐도 됨 |

---

## 3. 읽는 순서 가이드 (역할별)

### 처음 합류한 사람 (공통 최소 경로)
1. `PRD.md` §1~§4 (무엇을 왜 만드는가, FR-01~09)
2. `docs/research/selectai-reference.md` §1·§10 (액션 목록과 구현 주의사항 — "왜 GENERATE 패턴인가")
3. 이후 역할별 경로로 분기.

### 백엔드 개발자
`PRD.md` → `selectai-reference.md`(전체 정독) → `architecture.md` → `api-spec.md`(구현 계약) → `security.md`(S1~S11 체크리스트)

### 프론트엔드 개발자
`PRD.md` → `design.md`(페이지/상태/인터랙션) → `style.md`(토큰/컴포넌트) → `api-spec.md`(요청/응답 스키마) → `selectai-reference.md` §1·§3(액션·속성 해설 문구 원천)

### 시연자 (Presales/영업/파트너)
`demo-scenarios.md`(§1 또는 §2 시나리오 + §5 리허설 체크리스트) → 필요 시 `PRD.md` §3(페르소나별 사용법) → 데모 종료 후 `security.md` §6(정리 체크리스트)

### QA
`PRD.md` §4(FR 수용 기준) → `demo-scenarios.md` §6(QA 계획) → `api-spec.md`(오류 코드·스키마 검증 기준)

---

## 4. 문서 간 기준(단일 소스) 규칙

충돌 발견 시 아래 우선순위로 판정한다.

| 영역 | 기준 문서 |
|---|---|
| Select AI 기술 사실 (액션명·프로시저명·속성명·권한 SQL) | `docs/research/selectai-reference.md` (최우선, 추측 금지) |
| 기능 범위·우선순위(P0/P1/P2)·수용 기준 | `PRD.md` |
| API 경로·요청/응답 스키마·오류 코드 | `docs/api-spec.md` |
| 아키텍처 결정(호출 패턴, 저장 방식, 배포, O1~O5 결정) | `docs/architecture.md` |
| 화면 구조·인터랙션·설계 전제 1~5 | `design.md` |
| 시각 토큰·컴포넌트 스타일 | `style.md` |
| 보안 불변 조건(암호화·마스킹·읽기 전용 게이트) | `docs/security.md` |
| 데모 진행·질문 라이브러리·QA 시나리오 | `docs/demo-scenarios.md` |

공통 합의 사항(전 문서 공유):
- 액션 표기: P0 = `runsql`/`showsql`/`explainsql`/`narrate`/`chat`, P1 = `showprompt`/`feedback`, P2 = `summarize`/`translate`, 범위 외 = `agent`. **`showparameter`는 존재하지 않는 액션 — 사용 금지.**
- 증강 비교 프로파일 쌍 이름: `ENRICH_DEMO_OFF` / `ENRICH_DEMO_ON` (api-spec §7.4 base_name 기본값).
- 모호 데모 스키마: `TABLE1(c1,c2,c3)`·`TABLE2(c1,c6,c7)`·`TABLE3(c1,c4,c5)` (api-spec §7.1).
- Resource Principal 활성화 프로시저: `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI')` (`ENABLE_RESOURCE_PRINCIPAL` 아님).
- Data Access 제어: `DBMS_CLOUD_AI.ENABLE_DATA_ACCESS` / `DISABLE_DATA_ACCESS`.

---

## 5. 미해결/결정 완료 이슈 (교차 검토 후속)

> 교차 검토에서 식별한 X1~X6 미해결 이슈는 전부 결정 완료되어 §5.1에 반영했다.

### 5.1 결정 반영 완료

| # | 결정 | 반영 문서 |
|---|---|---|
| X1 | 암호화 마스터 키: `APP_SECRET_KEY` 우선, 미설정 시 `~/.selectai/secret.key` 자동 생성 + 경고(평문 폴백은 금지). 키-데이터 분리 불변 | security.md §2.1, architecture.md §3.3 |
| X2 | 생성 리소스 대장은 P0 채택. `~/.selectai/resources.json` JSON 파일 ledger와 `GET /api/v1/resources`·`DELETE /api/v1/resources/{id}`·`POST /api/v1/resources/cleanup` CRUD, PG-08 "데모 환경 정리"를 명세화 (SQLite 미사용) | PRD, architecture, api-spec, design, security |
| X3 | **대상 테이블은 사용자가 선택한다(불변 원칙)** — 프로파일의 `object_list`는 인증한 커넥션 사용자가 DB에서 볼 수 있는(`ALL_*` 뷰) 테이블 중 PG-03a 브라우저로 고른 것으로 구성한다. 앱이 시드/검증해 제공하는 SH·무비 모호 스키마는 **데모 편의용 프리셋**일 뿐 대상 선택을 제한하지 않는다. 한국형 `SALES_DEMO` 프리셋은 검증 전까지 P1 보류 | PRD(FR-04), design(PG-03a), api-spec(§8), security(§4.2), demo-scenarios(§3) |
| X4 | 단순/전문가 모드, SQL 투명 모드, 가이드 투어는 프런트 `localStorage` 저장. 백엔드는 기본 프로파일만 영속 | architecture, design |
| X5 | Hugging Face는 P0 provider enum에서 제외. UI 선택지는 `oci/openai/azure/cohere/google/anthropic/aws`, 기타는 고급 JSON 입력으로 우회 | PRD, api-spec, selectai-reference |
| X6 | 무비 증강 시드는 `backend/seeds/movie_schema.sql`, `movie_comments.sql`, `movie_reset.sql` 3파일 체계로 통일 | architecture, api-spec, demo-scenarios |
