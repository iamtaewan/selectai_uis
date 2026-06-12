# 전체 오류 검토 보고서

- **검토일**: 2026-06-12
- **검토 방식**: 3개 관점 병렬 검토 — ① PDF 원본 대조 기술 사실 검증, ② 문서 간 일관성 감사, ③ 문서 내부 결함 검토
- **대상**: PRD.md, design.md, style.md, docs/architecture.md, docs/api-spec.md, docs/security.md, docs/demo-scenarios.md, docs/INDEX.md, docs/research/selectai-reference.md

## 총평

- 핵심 기술 사실(액션 10종, 프로시저명, 권한 SQL, 오류 메시지, 모델명, 프로파일 속성 21개)은 **PDF와 전수 대조 결과 정확**. `showparameter` 부재 판정도 PDF 전문 검색(0건)으로 재확인됨.
- 이전 교차 검토에서 수정한 핵심 항목(액션 목록, 프로파일 쌍 명칭, OCID, 프로시저 패키지 소속, 모호 스키마 구조)은 안정적으로 수렴됨.
- 최초 검토 시 잔여 오류 **총 36건**: 시급(높음) 2건, 중간 11건, 낮음/경미 23건. 아래 상세 표는 발견 당시 스냅샷이며, 반영 완료 항목은 §0에 별도 기록한다.

---

## 0. 후속 반영 현황 (2026-06-12)

| 항목 | 상태 |
|---|---|
| X2 | P0 채택. PRD FR-10, architecture ledger, api-spec `GET/POST /api/v1/cleanup`, design PG-08, security cleanup 기준 반영 |
| X3 | P0은 SH + admin `TABLE1`/`TABLE2`/`TABLE3` 무비 모호 스키마로 확정. `SALES_DEMO`는 P1 후보로 보류 |
| X4 | 단순/전문가 모드, SQL 투명 모드, 가이드 투어는 프런트 `localStorage`; 백엔드 영속은 기본 프로파일만 유지 |
| X5 | Hugging Face는 provider enum 제외. UI 선택지는 `oci/openai/azure/cohere/google/anthropic/aws`, 기타는 고급 JSON/`provider_endpoint` |
| X6 | 무비 증강 시드 파일명을 `backend/seeds/movie_schema.sql`, `movie_comments.sql`, `movie_reset.sql`로 통일 |
| H1/H2 | 챗봇 `params_json` 바인드 패턴과 Resource Principal Dynamic Group 정책문 반영 |
| M1/M2/M3/M6/M7/M8 | feedback UI 위치, showparameter QA 범위, pool min=0, 클릭 목표, SQL 미리보기 원칙, chat compare 병렬 실행 정렬 완료 |

---

## 1. 시급 수정 (높음) — 실행 차단성 오류

| # | 위치 | 내용 | 수정 방향 |
|---|------|------|----------|
| H1 | api-spec.md:760 | §6.2 챗봇 내부 SQL이 `params => '{"conversation_id":"' \|\| :conversation_id \|\| '"}'` 로 JSON을 문자열 연결로 조립 — 문서 스스로 세운 "바인드 변수 단일 패턴" 원칙(§1.6, §5.2)의 유일한 위반. JSON 파손/주입 여지 | `json.dumps()`로 직렬화한 JSON 전체를 `:params_json` 단일 바인드로 전달 (§5.2와 동일 패턴) |
| H2 | security.md:161-164 | Resource Principal용 Dynamic Group 정책문이 `allow group <group-name> ...` — `group`은 사용자 그룹 구문. 이대로 따라 하면 RP 인증 실패 | `allow dynamic-group <dynamic-group-name> to manage generative-ai-family in compartment TAEWAN.KIM` |

## 2. 중간 심각도 — 구현 착수 전 정리 필요

### 문서 간 불일치 (5건)

| # | 위치 | 내용 | 기준 문서 |
|---|------|------|----------|
| M1 | style.md:257 | feedback을 P1 "탭"으로 표기 — design.md:394는 feedback을 결과 카드 👍/👎 버튼으로 통합 (탭은 showprompt만) | design.md |
| M2 | demo-scenarios.md:307 | QA-05 "UI 어디에도 showparameter 문자열 부재" 정적 검사 — design.md PG-03b의 학습 메모("showparameter 액션이 없습니다…")가 존재하므로 이 검사는 반드시 실패 | 검사 범위를 "액션 선택지/실행 경로"로 한정 + 학습 메모 예외 명시 |
| M3 | api-spec.md:1370 | 커넥션 풀 `min=1` vs architecture.md:223 `min=0`(lazy 생성, 근거 있는 아키텍처 결정) | architecture.md (min=0) |
| M4 | security.md:47 | 암호화 키 환경변수 `APP_MASTER_KEY` vs architecture.md `APP_SECRET_KEY` | architecture.md (APP_SECRET_KEY) — X1 이슈에 변수명 통일도 추가 필요 |
| M5 | api-spec.md:1381-1382 | call_timeout 세분화(권한 30s, showsql 60s) vs architecture.md `SELECTAI_CALL_TIMEOUT_MS=120000` 단일값 | 양쪽 정렬 필요 — api-spec 세분화 채택 시 architecture §3.2/§6.3 환경변수 설계 갱신 |

### 문서 내부 결함 (6건)

| # | 위치 | 내용 | 수정 방향 |
|---|------|------|----------|
| M6 | design.md:137 | "클릭 3회 이내 첫 질문 실행" — "칩 클릭=입력만(자동 실행 금지)"(396, 542) 및 "LLM 호출은 명시적 버튼만"(556)과 모순 (실제 최소 5클릭) | "클릭 3회 이내 시연 화면 도달"로 목표 재정의 |
| M7 | architecture.md:23 | "FR-03/04 미리보기도 GENERATE 패턴만 노출" — 해당 미리보기는 GRANT/ACL/CREATE_PROFILE SQL이므로 성립 불가, §3.4와 모순. `select ai` grep 금지 규칙도 §4.1 학습용 참고 문자열 기능과 충돌 | "미리보기에 SET_PROFILE/SELECT AI 키워드를 포함하지 않는다"로 의도 정정 + 학습용 문자열은 프런트 정적 텍스트로 명시 |
| M8 | api-spec.md:801↔1384 | chat/compare가 §6.7 "순차 실행" vs §11.2 "asyncio.gather 병렬" 자기모순 | 병렬로 통일 (§6.7 수정) |
| M9 | api-spec.md:427-428 | model enum 값에 `"cohere.command-r-16k (deprecated)"` 문자열 포함 — 그대로 전송 시 무효 모델명 | `deprecated: true` 별도 필드 분리 |
| M10 | api-spec.md:1400-1401 | per-conversation `asyncio.Lock`은 프로세스 메모리 상태 — stateless 선언과 모순, 멀티 워커에서 무력화 | 단일 워커 전제 명시 또는 DB 기반 잠금 |
| M11 | security.md:109↔115 | 수동 오버라이드가 열린 읽기 전용 게이트를 "프롬프트 인젝션 최종 방어선"으로 규정 — 인젝션이 확인 클릭 유도 가능 | LLM 경로 비SELECT 전면 차단 또는 "최종 방어선" 표현 완화 |

### 기술 근거 문서 보강 (1건)

| # | 위치 | 내용 | 수정 방향 |
|---|------|------|----------|
| M12 | selectai-reference.md §7 | "comments 미사용 시 QUANTITY_SOLD 등 잘못된 컬럼 선택" 전/후 비교 서사는 PDF에 없는 외삽 — PDF p148-149에서 QUANTITY_SOLD는 comments **활성** 상태 출력에 등장 | "PDF는 전/후 비교를 직접 보여주지 않으며, comments의 정확도 향상 일반 원칙(p25, p147)에 기반한 데모 자체 설계임"을 명시 |

## 3. 낮음/경미 (23건 요약)

**selectai-reference.md (3건)**
- region 기본값 "us-chicago-1 계열" — 본 PDF에 근거 없음 (Supplied Package Reference 확인 필요로 표기 변경)
- §7 무비 스키마 예제의 provider를 azure→oci로 각색한 사실 미표기
- DBA_CLOUD_AI_CONVERSATIONS 인용 페이지 오기 (p256→p133-135)

**문서 간 (3건)**
- architecture.md:325 — §5.1 다이어그램의 `GET /conversations/{uuid}/prompts` 경로가 api-spec에 미정의 (`/chat/conversations/{id}/messages`가 정식)
- architecture.md:204 — wallet 검증 파일 목록에 `cwallet.sso` 누락 (api-spec·design은 허용)
- demo-scenarios.md:137·168 — 모호 스키마를 별도 스키마 `MOVIE_OBSCURE`로 명명 vs architecture/api-spec은 "admin 스키마 하위 TABLE1~3"

**PRD.md (1건)**: :21 "최소 5단계" 수치와 나열(6단계) 불일치

**design.md (2건)**: :72 가드레일 절의 잠금/허용 혼재 서술, :192 ORA-12506 라벨 오류(타임아웃 아님 — 리스너 연결 거부)

**style.md (1건)**: :36 원칙 A6의 Redwood Red 허용처 목록에 "활성 탭 인디케이터" 누락 (§2·§5.3과 불일치)

**api-spec.md (7건)**
- :160↔1041 — `Literal["admin","ADMIN"]` 검증 실패는 422인데 명세는 400 ADMIN_ONLY
- :477 — §4.2 미리보기 예시 요청(oci)과 응답 경고(openai ACL)가 불일치
- :37 — "§3 이후 전부 X-Connection-Id 필요" 서술과 정적 엔드포인트(§4.1, §5.1, §5.4) 모순 — 단서 추가
- :102 — ORA-00923을 400으로 분류했으나 메시지 스스로 백엔드 버그 가능성 언급 → 500이 정합
- :1232-1239 — FeedbackRequest sql_id/sql_text one-of 검증 규칙·오류 케이스 미정의
- :358-361 — data_access PL/SQL 익명 블록 2개에 종결 `/` 1개 (스크립트 실행 불가)
- :808-816↔1283-1285 — §6.7 응답 예시가 ChatCompareResult 스키마의 필수 필드 누락

**api-spec.md 추가 (1건)**: :61↔377·501·674·813 — executed_sql 표현 규칙(바인드 유지/리터럴 치환/혼합)이 문서 안에서 3가지로 혼재

**security.md (1건)**: :56↔66 — "절대 금지" 표 안에 "일부 표시 허용" 항목 혼재

**demo-scenarios.md (3건)**
- :136↔68·121·199·269 — §3.1은 ④⑤에 SALES_DEMO 권장 배정인데 표준/단축 시나리오·리허설 질문은 전부 SH 전제 (사용 스키마 프리셋 명시 필요, X3과 연동)
- :154-157 — 생성 SQL 방침 코드블록에 실DDL과 타입 없는 의사 표기 혼재
- :166 — "한국어 값 비교를 위해 case_sensitive_values=false" — 한국어는 대소문자 없음, 실효는 영문 코드값

## 4. 검증 통과 항목 (수정 불필요)

- showparameter 언급 17건 전수 — 모두 "존재하지 않음 설명/금지" 맥락, 기능처럼 남은 곳 0건
- 액션 목록·FR ID·PG ID·컴파트먼트 OCID(7개 문서 10곳)·프로시저 패키지 소속·모호 스키마 구조(c1~c7) — 전 문서 정합
- mermaid 다이어그램 6개 전부 렌더링 가능, Pydantic v2 문법 일관(v1 혼용 없음)
- PDF 대조: 액션 표(p43-44), ENABLE_PRINCIPAL_AUTH(p81), ACL 불필요(p34), 모델 표(p15), Conversations(p42·47·125-132), feedback 권한(p64), DATA_ACCESS(p174-175), 프로파일 속성 20/21, CREATE_PROFILE 구문 — 전부 일치

---

## 반영 이력 (개발 착수 시)

- **검토 시점**: 2026-06-12 (명세 정리 에이전트 1/8). 각 항목은 수정 전 grep/Read로 현재 상태 확인 후 잔여분만 반영.

### 신규 수정한 항목

| 항목 | 파일:변경요약 |
|---|---|
| M5 | architecture.md:456 — `SELECTAI_CALL_TIMEOUT_MS=120000`을 "GENERATE 계열 call_timeout 상한(120s)"으로 명시하고, 단계별 세분값(showsql 60s·권한 30s 등)은 api-spec §12.2 표를 따르며 상한을 넘지 않는다고 정렬 문구 추가. 양 문서 GENERATE 120s 기준 정합 |
| M9 | api-spec.md:496-503 — model enum 값에서 `(deprecated)` 접미사 제거(순수 모델명 `cohere.command-r-16k`·`cohere.command-r-plus`). 별도 `"deprecated": [...]` 필드 추가 + description_ko에 "UI 비활성/경고 배지 표기, 전송 값은 순수 모델명" 명시 |
| M11 | security.md:118,124 — 읽기 전용 게이트를 "LLM 생성 SQL 경로 비SELECT 자동 차단(수동 오버라이드 없음, 실행 버튼 비활성)"으로 강화. §3.4의 "최종 방어선" 모순 해소 — 인젝션이 확인 클릭을 유도해도 파괴적 SQL 미실행. 고정 템플릿 DDL 경로(§3.3)는 분리 유지 |
| L(design ORA-12506) | design.md:240 — `ORA-12506 (게이트웨이 타임아웃)` 라벨을 `ORA-12506 (리스너 연결 거부)`로 정정. 조치 문구("ADB 중지 상태 확인")는 ORA-12506 의미와 부합하여 유지 |
| L(PL/SQL 종결자) | api-spec.md:430-433 — data_access 익명 블록 2개(ENABLE/DISABLE)가 `/` 1개만 공유 → 각 블록에 `/` 부여(상호 배타 변형, enable 플래그로 택1) + 주석 명확화 |

### 이미 수정되어 건너뛴 항목 (현재 상태 확인 완료)

- **H1** — api-spec.md §6.2(:828-837): `params => :params_json` 단일 바인드 + "백엔드가 `json.dumps({"conversation_id": ...})`로 직렬화, SQL 문자열 연결 금지" 문구 이미 반영. 문자열 연결(`||`) 패턴 없음. (§11.2 :888 executed_sql 예시의 리터럴 JSON은 학습용 표시 표현이며 SQL 조립 패턴 아님)
- **H2** — security.md:173: `allow dynamic-group <dynamic-group-name> to manage generative-ai-family in compartment TAEWAN.KIM` 이미 반영. `allow group ...` 잔존 없음
- **M1** — style.md:257: feedback을 "결과 카드 👍/👎 버튼으로 통합, 탭은 showprompt만(P1 배지)"으로 이미 정정됨
- **M2** — demo-scenarios.md:294 QA-05: 검사 범위 "액션 선택지/실행 경로에 부재 + PG-03b 학습 메모 정적 문구 예외"로 이미 한정됨
- **M3** — api-spec.md:1615 / architecture.md:267·488: 풀 `min=0` 이미 통일됨
- **M8** — api-spec.md §6.7(:878) "두 호출은 병렬 실행한다" + §12.2(:1629) "`asyncio.gather` 병렬" 이미 정합. 자기모순 없음
