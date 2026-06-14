# 데모 시나리오 & QA 가이드 — Select AI Demo Studio

| 항목 | 내용 |
|---|---|
| 문서 버전 | v1.0 (2026-06-12) |
| 작성자 | 데모 시나리오 전문가 / QA 리드 (전문가 8/8, 오라클 Presales 관점) |
| 기준 문서 | `PRD.md` v1.0, `docs/research/selectai-reference.md` (Select AI User's Guide 26ai, G35918-05) |
| 대상 독자 | Presales SE(P1 박선영), 영업 대표(P2 김재현), 파트너 엔지니어(P3 이민호), 개발팀/QA |

> **시나리오 공통 원칙 (PRD §6 아키텍처 결정 준수)**
> - 앱이 실행하는 모든 Select AI 호출은 `DBMS_CLOUD_AI.GENERATE(prompt, profile_name, action, params)` 단일 패턴이다. `SELECT AI` 키워드·`SET_PROFILE`·`SET_CONVERSATION_ID`는 화면 어디에도 등장하지 않는다 — 데모 멘트에서도 "세션에 의존하지 않는 호출"임을 강조 포인트로 활용한다.
> - 모든 실행 화면의 "실행된 SQL 보기" 펼침 영역이 데모의 숨은 주인공이다. 파트너/기술 청중 앞에서는 반드시 한 번 이상 펼쳐서 보여준다.
> - `showparameter`라는 액션은 존재하지 않는다. 시연자 멘트에서도 사용 금지. 속성 확인은 "프로파일 상세(속성 뷰)" 화면으로 안내한다.

---

## 1. 표준 데모 시나리오 (20분)

**전제**: 리허설 체크리스트(§5) 완료 상태. 신규 환경 기준 시나리오이며, 저장된 커넥션·프로파일 재사용 시 1~3단계를 1분으로 압축할 수 있다.

**전체 타임라인**

| 구간 | 시간 | 화면 | 데모 가치 |
|---|---|---|---|
| ① DB 연결 | 0:00–2:00 | 연결/커넥션 관리 | "wallet 업로드 한 번이면 끝" |
| ② 권한 사전 점검 | 2:00–4:30 | 권한 점검 | "ORA 오류 없는 데모 환경, 원클릭 복구" |
| ③ 프로파일 생성 | 4:30–8:00 | 프로파일 설정 | "속성 하나하나가 한국어로 설명되는 학습 도구" |
| ④ 액션 비교 | 8:00–12:30 | 액션 시연 | NL2SQL 핵심 — 같은 질문, 5가지 액션 |
| ⑤ 챗봇 | 12:30–16:00 | 챗봇 | 멀티턴 맥락 + 맥락 유/무 비교 |
| ⑥ Comment 증강 (클라이맥스) | 16:00–19:30 | 증강 전/후 비교 | "메타데이터가 정확도를 만든다" |
| ⑦ 클로징 | 19:30–20:00 | 대시보드/요약 | 비즈니스 가치 정리 |

### ① DB 연결 (0:00–2:00) — FR-01/FR-02

| 단계 | 시연자 행동 | 화면/예상 결과 |
|---|---|---|
| 1 | [연결] 화면 → wallet zip 드래그&드롭 | `tnsnames.ora`에서 TNS alias 목록 자동 추출 (`<db>_high/_medium/_low`) |
| 2 | `_low` 또는 `_medium` alias 선택, admin 비밀번호 입력 → [연결 테스트] | 5초 내 성공 배지 + DB 버전(26ai)·인스턴스명·현재 사용자(ADMIN) 표시 |
| 3 | 커넥션 이름(예: `demo-adb-26ai`) 입력 → [저장] | 커넥션 목록에 등장, "자격 정보는 서버에 암호화 저장" 안내 문구 |

**고객 강조 멘트**: "보통 wallet 구성과 접속 설정만으로 30분이 걸립니다. 여기서는 zip 파일 하나 올리면 TNS alias까지 자동으로 읽어옵니다. 다음 데모부터는 저장된 커넥션을 클릭 한 번으로 불러옵니다."

### ② 권한 사전 점검 (2:00–4:30) — FR-03

| 단계 | 시연자 행동 | 화면/예상 결과 |
|---|---|---|
| 1 | [권한 점검] 화면 → [전체 점검 실행] | 항목별 신호등: `DBMS_CLOUD_AI` EXECUTE / 자격증명(credential 또는 Resource Principal) / **Data Access 활성 여부** / 네트워크 ACL |
| 2 | ACL 항목이 "필요 없음(OCI GenAI)" 회색 처리된 것을 가리킴 | OCI Generative AI는 ACL이 불필요(가이드 p34)하다는 한국어 설명 표시 |
| 3 | 미충족 항목(예: Resource Principal 미활성) 클릭 → 실행될 SQL 미리보기 확인 → [적용] | `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI')` 전문이 미리보기로 노출 후 적용, 자동 재점검 → 전 항목 녹색 |

**고객 강조 멘트**: "데모 현장에서 가장 무서운 게 ORA 오류죠. 이 화면은 Select AI의 사전 요구 사항을 매뉴얼 페이지 근거와 함께 점검하고, 부족한 것은 실행될 SQL을 먼저 보여준 뒤 원클릭으로 적용합니다. 특히 'Data Access' 항목 — 이게 꺼져 있으면 자연어 서술(narrate)이 ORA-20000으로 실패하는데, 미리 잡아줍니다."

### ③ 프로파일 생성 (4:30–8:00) — FR-04/FR-05

| 단계 | 시연자 행동 | 화면/예상 결과 |
|---|---|---|
| 1 | [프로파일 설정] → 새 프로파일 `SH_GENAI` | 기본값 자동 채움: provider `oci`, model `meta.llama-3.3-70b-instruct`, region `us-chicago-1`, compartment(TAEWAN.KIM OCID) |
| 2 | `object_list` 체크박스 브라우저에서 데모 스키마 테이블 선택 | 선택 즉시 JSON 미리보기 갱신 |
| 3 | 속성 2~3개의 한국어 해설 툴팁을 일부러 열어 보임 — 추천: `comments`(뒤에 복선), `enforce_object_list`, `temperature` | 해설 + 매뉴얼 근거 페이지 표시 |
| 4 | `CREATE_PROFILE` PL/SQL 미리보기 펼침 → [생성] → [기본 프로파일로 지정] | 프로파일 목록에 등장, "기본 프로파일은 앱 설정으로 저장되어 매 호출에 명시 전달됩니다" 안내 |

**고객 강조 멘트**: "21개 속성 전부 한국어 설명이 붙어 있어서, 이 도구는 데모 도구이자 Select AI 교과서입니다. 특히 `comments` 속성 — 이게 오늘 데모의 마지막 하이라이트가 됩니다. 그리고 생성 버튼이 실제로 어떤 PL/SQL을 실행하는지 항상 투명하게 보여드립니다."

### ④ 액션 비교 시연 (8:00–12:30) — FR-06

동일한 질문 1개를 5개 액션 탭으로 전환하며 실행한다. 추천 질문(추천 프롬프트 버튼 제공):

> **"샌프란시스코에 사는 결혼한 고객은 몇 명인가요?" / "how many customers in San Francisco are married"** (SH 스키마, 가이드 p75 검증 예제)

| 액션 탭 | 예상 결과 | 멘트 |
|---|---|---|
| `runsql` | 결과 표(grid) + 응답 시간 | "자연어가 곧바로 데이터가 됩니다. 기본 액션입니다." |
| `showsql` | 생성 SQL만 구문 강조 표시 | "실행 전에 SQL을 검토하고 싶은 DBA를 위한 모드입니다." |
| `explainsql` | SQL + LLM의 자연어 설명 | "생성된 SQL을 LLM이 스스로 해설합니다. SQL 교육에도 쓰입니다." |
| `narrate` | 실행 결과를 자연어 문장으로 서술 | "결과를 보고서 문장처럼 받아볼 수 있습니다. 임원 보고 자동화의 시작점이죠." |
| `chat` | LLM 직접 응답(데이터 미접근) | "이건 일반 LLM 대화 모드 — DB 데이터를 쓰는 narrate와의 차이를 보세요." |

마무리로 [실행된 SQL 보기] 펼침 → `DBMS_CLOUD_AI.GENERATE(... action => 'narrate' ...)` 원문 노출.

**고객 강조 멘트**: "이 모든 게 데이터베이스 안의 함수 호출 하나입니다. 별도 미들웨어 없이 SQL이 닿는 모든 곳 — 애플리케이션, APEX, 리포트 — 에서 같은 방식으로 쓸 수 있습니다. 그리고 중요한 것: SQL 생성 시 LLM에는 스키마 메타데이터만 전달되고 실제 데이터는 전송되지 않습니다(narrate만 예외이며 이것도 관리자가 차단할 수 있습니다)."

### ⑤ 챗봇 시연 (12:30–16:00) — FR-07

| 단계 | 시연자 행동 | 예상 결과 |
|---|---|---|
| 1 | [챗봇] → [새 대화] (title 기본값 그대로) | `CREATE_CONVERSATION`으로 UUID 발급, 대화 시작 |
| 2 | 질문 1: "전체 고객 수는 몇 명인가요?" / "what are the total number of customers" | 55500 류의 답변 (액션 `narrate` 기본) |
| 3 | 질문 2: "그걸 국가별로 나눠서 보여줘" / "break out count of customers by country" | **이전 질문의 '고객 수' 맥락을 유지**한 국가별 분포 |
| 4 | 질문 3: "구매액 기준 상위 5명만 남기고 순위를 붙여줘" / "keep the top 5 customers and their country by their purchases and include a rank in the result" | 멀티턴 맥락 누적 시연 (가이드 p125–126 검증 시퀀스) |
| 5 | [맥락 비교 모드] 토글 → 질문 2를 conversation_id 없이 재실행 | 좌(맥락 없음: 모호하거나 다른 답) / 우(맥락 있음: 정확한 후속 답) 나란히 표시 (p132 근거) |

**고객 강조 멘트**: "'그걸', '거기에' 같은 대명사가 통합니다. 오른쪽 비교 화면이 핵심인데 — 대화 ID 없이 같은 질문을 던지면 맥락이 사라집니다. 이 대화 이력은 DB 안에 영구 저장되고 retention 정책으로 관리됩니다. 챗봇 상태 관리를 애플리케이션이 아니라 데이터베이스가 해준다는 뜻입니다."

### ⑥ Comment 증강 전/후 비교 — 클라이맥스 (16:00–19:30) — FR-08

| 단계 | 시연자 행동 | 예상 결과 |
|---|---|---|
| 1 | [증강 비교] → [데모 스키마 원클릭 생성] | 모호 컬럼명(c1~c7) 무비 테이블 + comments off/on 프로파일 쌍 자동 생성 |
| 2 | 질문 입력: "총 시청 횟수는 얼마인가요?" / "what are our total views" → [전(comments off) 실행] | **오답 SQL** — c7(시청 수) 대신 엉뚱한 컬럼/테이블 선택 (가이드 p147–150 패턴) |
| 3 | "왜 틀렸을까요? 사람도 c7이 뭔지 모르잖아요" 멘트 후 COMMENT 폼 열기 | 테이블/컬럼별 COMMENT 입력 폼 + `COMMENT ON ...` DDL 미리보기 |
| 4 | 준비된 코멘트 세트 [일괄 적용] (예: `c7` → 'number of views, watched, streamed') | DDL 실행 완료 표시 |
| 5 | [후(comments on) 실행] → 좌우 분할 비교 | 좌: 오답 SQL/결과, 우: **c7을 SUM하는 정답 SQL**/결과 |
| 6 | (기술 청중일 때, P1) `showprompt`로 증강 프롬프트에 COMMENT가 포함된 것 확인 | LLM에 전달된 프롬프트 원문에 코멘트 문구 노출 |

**고객 강조 멘트 (클로징 겸용)**: "방금 모델을 바꾸지도, 재학습하지도 않았습니다. **데이터베이스가 이미 가진 메타데이터를 LLM에 보여줬을 뿐입니다.** 이것이 'AI를 데이터로 가져오는' Oracle의 접근입니다. 고객사의 실제 스키마에 코멘트·제약조건이 잘 정리되어 있을수록 Select AI는 더 정확해집니다 — 데이터 거버넌스 투자가 곧 AI 정확도 투자가 되는 겁니다."

### ⑦ 클로징 (19:30–20:00)

- (P1 구현 시) 데모 상태 대시보드 신호등을 보여주며 "다음 데모는 이 화면 확인 후 3분이면 시작"으로 마무리.
- 요약 3문장: 자연어→SQL→실행이 DB 함수 하나 / 대화 상태도 DB가 관리 / 메타데이터 증강으로 정확도는 운영하면서 좋아진다.

---

## 2. 단축 데모 (5분) — 영업 대표(P2)용 최소 경로

**전제**: Presales가 사전 구성 완료(커넥션·프로파일·데모 스키마·코멘트 세트 모두 준비, 대시보드 전 항목 녹색). 영업 대표는 클릭과 준비된 멘트만 수행한다. **타이핑 0회 목표** — 모든 질문은 추천 프롬프트 버튼으로 실행.

| 시간 | 행동 | 멘트 |
|---|---|---|
| 0:00–0:30 | 앱 접속 → 저장된 커넥션 자동 선택 확인 (대시보드 녹색) | "지금 보시는 건 OCI의 Autonomous AI Database에 바로 붙어 있는 화면입니다." |
| 0:30–2:00 | [액션 시연] → 추천 질문 버튼 "샌프란시스코의 결혼한 고객 수" → `runsql` 결과 표 | "영어든 한국어 질문 버튼이든, SQL을 몰라도 데이터가 나옵니다." |
| 2:00–3:30 | [챗봇] → 준비된 대화에서 후속 질문 버튼 "국가별로 나눠줘" | "방금 질문을 기억하고 이어서 답합니다. 사내 데이터 챗봇이 이렇게 만들어집니다." |
| 3:30–4:45 | [증강 비교] → 미리 실행해 둔 전/후 비교 결과 화면 열기 (라이브 재실행 불필요) | "왼쪽은 설명 없는 스키마라 틀렸고, 오른쪽은 컬럼 설명만 넣었더니 정답입니다. 모델 교체 없이요." |
| 4:45–5:00 | 클로징 | "자세한 기술 검증은 저희 솔루션 엔지니어가 PoC로 보여드리겠습니다." |

**실패 대비 단순 UX**: 어떤 단계든 오류 시 [다시 시도] 버튼 1회 → 그래도 실패하면 증강 비교의 **저장된 비교 결과 화면**(라이브 호출 불필요)으로 건너뛰어 마무리한다.

---

## 3. 샘플 데이터셋 제안

### 3.1 P0/P1 데이터셋 전략 (결정)

| 범위 | 데이터셋 | 용도 | 근거 |
|---|---|---|
| **P0** | **SH 샘플 스키마** | 단계 ④ 액션 비교, ⑤ 챗봇 | 가이드 검증 질문과 정답 패턴이 이미 확인된 표준 스키마. MVP 데모 실패 리스크가 낮음 |
| **P0** | **admin 하위 `TABLE1`/`TABLE2`/`TABLE3` 무비 모호 스키마** | 단계 ⑥ 증강 전/후 비교 전용 | 가이드 ch19 p147–150의 "c1~c7 모호 컬럼" 패턴과 일치 |
| **P1 후보** | `SALES_DEMO` — 한국형 영업/주문 스키마 | 한국 고객 친화형 확장 데모 | PDF 근거 없는 자체 설계라 LLM 응답 검증 전까지 MVP 범위에서 제외 |

> X3 결정: P0 추천 질문 라이브러리는 SH 프리셋을 기본 노출한다. `SALES_DEMO` 질문은 코드와 QA 정답 세트가 검증된 뒤 P1 프리셋으로 추가한다.

> **대상 테이블은 프리셋에 한정되지 않는다(불변 원칙, X3)**: 위 SH·무비 스키마는 검증된 **프리셋**일 뿐이다. 시연자는 PG-03a의 스키마/테이블 브라우저에서 **인증한 커넥션 사용자가 DB에서 볼 수 있는 임의 테이블**(`ALL_*` 뷰 기반)을 골라 프로파일 `object_list`를 구성할 수 있다 — 고객 자신의 스키마로 즉석 시연할 때 이 경로를 사용한다(FR-04). 단, 프리셋 외 스키마는 가이드 검증 질문이 없으므로 LLM 응답 정확도는 보장되지 않음을 시연자에게 안내한다.

### 3.2 P1 후보: `SALES_DEMO` (영업/주문) — 보류 방침

`SALES_DEMO`는 한국어 고객명·도시·영업/주문 데이터가 직관적이라는 장점이 있으나, MVP P0에는 포함하지 않는다. 채택 전에는 다음 조건을 별도 이슈로 검증한다.

- SH 검증 질문과 동일한 유형의 정답 세트를 한국형 데이터에 심고, 리허설에서 LLM 생성 SQL을 확인한다.
- 테이블·컬럼 COMMENT와 FK 제약을 함께 설계해 `comments`/`constraints` 효과를 설명할 수 있게 한다.
- P1 채택 시 별도 시드 파일과 Cleanup ledger 리소스 타입을 추가한다. P0의 `backend/seeds/`에는 포함하지 않는다.

### 3.3 P0 무비 모호 스키마 (증강 비교 전용) — 시드 파일 방침

가이드 p147–150 패턴 준수:

```sql
-- api-spec.md §7.1과 동일 레이아웃 (c1 = 공통 조인 키)
CREATE TABLE table1 (c1 NUMBER, c2 VARCHAR2(200), c3 NUMBER);          -- 영화: id, 제목, 개봉연도
CREATE TABLE table2 (c1 NUMBER, c6 DATE, c7 NUMBER);                   -- 시청이력: 영화id, 시청일, 시청수
CREATE TABLE table3 (c1 NUMBER, c4 VARCHAR2(100), c5 VARCHAR2(100));   -- 사용자/디바이스: 영화id, 디바이스, 사용자
```

- 시드 파일은 3개로 통일한다(X6 결정).
  - `backend/seeds/movie_schema.sql`: `TABLE1`/`TABLE2`/`TABLE3` 생성 + 샘플 행. COMMENT는 넣지 않는다.
  - `backend/seeds/movie_comments.sql`: 데모 중 [일괄 적용] 버튼이 실행하는 COMMENT 세트.
  - `backend/seeds/movie_reset.sql`: COMMENT 제거, 데모 테이블/비교용 프로파일 쌍 정리 보조.
- `movie_comments.sql`의 핵심 COMMENT:
  - `table1` → 'Contains movies, movie titles and the year it was released'
  - `table1.c1` → 'movie ids. Use this column to join to other tables'
  - `table2.c7` → 'number of views, watched, streamed' (가이드 원문)
- comments off/on 프로파일 쌍(`ENRICH_DEMO_OFF` / `ENRICH_DEMO_ON` — api-spec §7.4 base_name 기본값)을 스키마 생성 시 함께 자동 생성. 두 프로파일은 `comments` 속성만 다르고 object_list 동일.
- **초기화 버튼은 `movie_reset.sql`을 기준으로 COMMENT 제거까지 포함**해야 함(`COMMENT ON ... IS ''`) — 전/후 비교를 반복 시연할 수 있도록.

---

## 4. 자연어 질문 라이브러리

### 4.1 액션별 검증 질문 (추천 프롬프트 버튼 세트)

표기: 한국어 / English. (SH)는 가이드 검증 예제 원문 기반이다. (SD)는 `SALES_DEMO` P1 후보 질문이며, P0 기본 UI에는 노출하지 않는다.

**`runsql` — 결과 표가 즉시 이해되는 질문**

| # | 질문 | 비고 |
|---|---|---|
| 1 | 전체 고객 수는 몇 명인가요? / how many customers exist | (SH p75, 정답 55500) |
| 2 | 샌프란시스코에 사는 결혼한 고객은 몇 명인가요? / how many customers in San Francisco are married | (SH p75) |
| 3 | 등급이 VIP인 고객은 몇 명인가요? / how many VIP grade customers are there | (SD) |
| 4 | 도시별 고객 수를 보여주세요 / show customer count by city | (SD) |
| 5 | 지난달 주문 금액 합계는 얼마인가요? / what is the total order amount for last month | (SD, 날짜 함수 생성 시연) |

**`showsql` — 생성 SQL 자체가 볼거리인 질문 (JOIN/집계)**

| # | 질문 | 비고 |
|---|---|---|
| 6 | 카테고리별 매출 합계를 보여주세요 / show total sales amount by product category | (SD, 3-테이블 JOIN 생성) |
| 7 | 주문이 한 번도 없는 고객을 찾아주세요 / find customers who have never placed an order | (SD, NOT EXISTS/외부조인 생성) |
| 8 | 매출 상위 5개 상품은? / what are the top 5 products by sales | (SD, FETCH FIRST 생성) |

**`explainsql` — 설명 들을 가치가 있는 복합 질문**

| # | 질문 | 비고 |
|---|---|---|
| 9 | 샌프란시스코의 결혼한 고객 수를 설명과 함께 보여주세요 / explain how many customers in San Francisco are married | (SH p75 검증) |
| 10 | 도시별 평균 주문 금액이 전체 평균보다 높은 도시를 찾아주세요 / find cities whose average order amount is above the overall average | (SD, 서브쿼리 해설 효과) |

**`narrate` — 문장 보고가 어울리는 질문**

| # | 질문 | 비고 |
|---|---|---|
| 11 | 샌프란시스코 상위 3명의 고객은 누구인가요? / what are the top 3 customers in San Francisco | (SH — 레퍼런스 §9 검증) |
| 12 | 이번 분기 매출 현황을 요약해 주세요 / summarize this quarter's sales performance | (SD) |
| 13 | 취소율이 가장 높은 상품 카테고리는? / which product category has the highest cancellation rate | (SD) |

**`chat` — 데이터 미접근 LLM 대화 (narrate와의 대비용)**

| # | 질문 | 비고 |
|---|---|---|
| 14 | 고객 세분화에 일반적으로 쓰는 기준을 알려줘 / what criteria are commonly used for customer segmentation | 일반 지식 — DB 무관함을 보여줌 |
| 15 | 시애틀과 샌프란시스코의 날씨 차이는? / What is the difference in weather between Seattle and San Francisco? | (가이드 p129 GENERATE 예제 원문) |

**챗봇 멀티턴 시퀀스 (가이드 p125–126 검증 시퀀스 + SD 이식)**

| 턴 | 질문 |
|---|---|
| 16 | 전체 고객 수는? / what are the total number of customers |
| 17 | 그걸 국가별로 나눠줘 / break out count of customers by country |
| 18 | 가장 많은 연령대는? / what age group is most common |
| 19 | 구매액 기준 상위 5명과 국가를 순위와 함께 보여줘 / keep the top 5 customers and their country by their purchases and include a rank in the result |
| 16'–19' | (P1 `SALES_DEMO` 후보) 전체 주문 건수는? → 그걸 도시별로 나눠줘 → 그중 수도권만 보여줘 → 상위 3개 도시에 순위를 붙여줘 |

### 4.2 Comment 증강 극적 비교 질문 (admin `TABLE1`/`TABLE2`/`TABLE3`)

설계 원칙: **증강 전에는 "그럴듯한 오답"**(틀린 컬럼 선택 또는 hallucinated 테이블)이 나오고, **증강 후에는 한 줄 SQL 정답**이 나오는 질문만 채택. 리허설에서 전/후 결과를 반드시 사전 확인(LLM 비결정성 대비, temperature 낮게 설정 권장 — 예: 0.2).

| # | 질문 | 증강 전 예상 (comments off) | 증강 후 예상 (comments on) |
|---|---|---|---|
| C1 | 총 시청 횟수는 얼마인가요? / what are our total views | c7의 의미를 몰라 COUNT(*)나 무관 컬럼 사용, 또는 실패 | `SELECT SUM(c7) FROM table2` 류 정답 (가이드 p147–150 원형) |
| C2 | 디바이스별 총 시청 횟수를 나눠 보여줘 / what are our total views broken out by device | 잘못된 그룹핑/컬럼 | 코멘트 기반 정확한 그룹핑 (가이드 p150 원문 질문) |
| C3 | 가장 많이 시청된 영화 제목은? / what is the most watched movie title | c2(제목)와 c7(시청 수)의 JOIN 경로를 찾지 못함 | c1 조인 코멘트('Use this column to join') 덕에 정확한 JOIN |
| C4 | 2020년 이후 개봉한 영화는 몇 편인가요? / how many movies were released after 2020 | c3이 연도인지 모름 → 오답/실패 | `WHERE c3 > 2020` 정답 |
| C5 | 월별 총 시청 횟수를 보여줘 / show total views by month | c6이 시청일임을 몰라 환각/오답 | c6(시청일) 코멘트 기반 정확한 GROUP BY |

> **시연 팁(Presales 관행)**: C1을 메인으로 라이브 실행하고, C2~C5는 보조 카드로 준비. 증강 전 단계에서 "오답"이 아니라 우연히 정답이 나오면 — "이번엔 운이 좋았네요"라고 받아치고 C3(JOIN 필요 질문)로 즉시 전환한다. JOIN 경로 추론은 코멘트 없이는 실패 확률이 훨씬 높다.

---

## 5. 데모 리허설 체크리스트

### 5.1 데모 전날 (D-1)

- [ ] **ADB 인스턴스 기동 상태** 확인 — Always Free/중지 정책으로 자동 stop 되었는지 OCI 콘솔에서 확인, 필요 시 Start (기동 수 분 소요)
- [ ] **컴파트먼트/리전 확인** — 프로파일 `oci_compartment_id`가 TAEWAN.KIM OCID(`ocid1.compartment.oc1..<your-compartment-ocid>`)인지, `region: us-chicago-1`인지 프로파일 상세 화면에서 확인
- [ ] **모델 가용성** — 기본 모델 `meta.llama-3.3-70b-instruct`로 `chat` 액션 1회 실제 호출(deprecated/리전 미지원 변동 대비). 실패 시 모델 목록에서 대체 모델(예: `cohere.command-r-plus-08-2024`) 선택 리허설
- [ ] **권한 점검 전 항목 녹색** — 특히 Data Access "활성" (ORA-20000 예방), Resource Principal 또는 credential 유효
- [ ] **데모 스키마 초기화** — SH 접근 가능 여부 확인, 무비 모호 스키마는 `movie_reset.sql` 후 `movie_schema.sql`로 재생성하고 **COMMENT 제거 상태**에서 시작(전/후 비교가 처음부터 가능하도록)
- [ ] **질문 라이브러리 전수 실행** — §4의 메인 질문(1, 2, 9, 11, 16–19, C1, C3)을 실제 실행해 응답·정답 확인, 응답 시간 기록
- [ ] **증강 전/후 결과 스크린샷 저장** — 라이브 실패 대비 폴백 자료
- [ ] wallet 만료일 확인(만료 임박 시 재다운로드)
- [ ] **wallet 자동 다운로드 사용 시** — 시연 장비에 OCI CLI 설치 확인 + `oci iam region list`로 `~/.oci/config` 인증 동작 확인 (실패 시 wallet zip 수동 업로드로 폴백 — api-spec §2.7)

### 5.2 데모 직전 (D-0, 30분 전)

- [ ] 커넥션 [테스트] 1회 (ADB 콜드 스타트/네트워크 점검 겸용)
- [ ] (P1 구현 시) 대시보드 전 항목 녹색 확인 — 미구현 시 권한 점검 화면 재실행으로 대체
- [ ] 챗봇 [새 대화] 1개 미리 생성 (현장에서 첫 호출 지연 흡수)
- [ ] 고객 프로젝터 해상도에서 좌우 비교 화면 가독성 확인

### 5.3 자주 발생하는 오류와 즉석 대처법

| 증상 | 원인 | 즉석 대처 | 데모 멘트로 전환 |
|---|---|---|---|
| `ORA-20000: Data access is disabled for SELECT AI` (narrate/합성 데이터) | 관리자가 `DISABLE_DATA_ACCESS` 실행 상태 | 권한 점검 화면 → Data Access 항목 [활성화] 원클릭 (`ENABLE_DATA_ACCESS`) | "보안 관리자가 LLM으로의 실데이터 전송을 차단할 수 있다는 거버넌스 기능입니다 — 일부러 보여드렸습니다" |
| 생성 SQL이 오답/실행 실패 (LLM 환각 — 가이드 공식 경고 p14·p45) | 비결정적 LLM 특성, 모호한 질문 | [다시 시도] 1회 → 검증된 추천 질문 버튼으로 교체 | "그래서 showsql로 SQL을 검토하고, feedback·comments로 정확도를 개선하는 기능이 함께 제공됩니다" |
| 프로파일 생성/호출 시 credential 오류 | Resource Principal 미활성, Dynamic Group 정책 누락, credential 오타 | 권한 점검 화면 재실행 → `ENABLE_PRINCIPAL_AUTH` 적용. 정책 문제면 API 서명 키 credential로 폴백 | (사전 점검으로 예방이 원칙 — 현장 발생 시 폴백 credential 사용) |
| 모델 호출 실패 (모델명/리전 불일치, deprecated) | 리전 모델 라인업 변동 | 프로파일 수정(`SET_ATTRIBUTE`)으로 모델 교체 — UI 미리보기로 SQL 확인 후 적용 | "프로파일 속성 하나만 바꾸면 모델이 교체됩니다 — 모델 종속성이 없다는 뜻이죠" |
| 첫 호출이 비정상적으로 느림 | ADB 콜드 스타트/풀 워밍업 | D-0 체크리스트의 사전 호출로 예방. 현장이면 chat 액션 가벼운 질문 먼저 | "첫 호출 워밍업 중입니다" |
| 커넥션 실패 (wallet/비밀번호) | wallet 만료, alias 오선택, admin 비밀번호 변경 | 저장된 예비 커넥션으로 전환(커넥션 2개 사전 저장 권장) | — |
| 외부 공급자 시연 중 호스트 접근 거부 | ACL 미적용 (외부 공급자만 해당) | 권한 점검에서 해당 공급자 host ACL [적용] (`APPEND_HOST_ACE`) | "OCI GenAI는 이 단계 자체가 필요 없습니다 — 그게 기본 공급자인 이유 중 하나죠" |
| 한국어 질문의 값 비교 실패 (대소문자/표기) | `case_sensitive_values` 설정, 시드 값 불일치 | 프로파일 `case_sensitive_values: "false"` 확인, 질문을 시드 값 표기와 일치시킴 | — |

---

## 6. QA 테스트 계획 요약

원칙: 각 FR의 PRD 수용 기준을 테스트 케이스로 1:1 매핑. 여기서는 **데모 성공에 직결되는 핵심 검증 시나리오**만 요약한다. (LLM 의존 케이스는 비결정성을 감안해 "구조 검증"과 "내용 검증"을 분리: 구조 검증은 자동화, 내용 검증은 리허설 체크리스트로 수동 수행.)

### 6.1 기능별 핵심 검증 시나리오

| ID | 대상 | 시나리오 | 합격 기준 |
|---|---|---|---|
| QA-01 | FR-01 | 정상 wallet zip 업로드 / 손상 zip / tnsnames.ora 누락 zip 3종 업로드 | 정상: alias 목록 추출·접속 성공·DB정보 표시. 비정상: 한국어 오류+해결 안내. 응답·로그에 비밀번호 평문 부재 (로그 grep 검증) |
| QA-02 | FR-02 | 커넥션 저장→재기동→목록→테스트→삭제 전체 라이프사이클 + 접속 불가 호스트 테스트 | 테스트 버튼 5초 내 결과(타임아웃 포함), 저장 파일에 자격 평문 부재, 마지막 사용 커넥션 기본 선택 |
| QA-03 | FR-03 | (a) 신규 사용자 권한 0 상태에서 점검→전 항목 적용→재점검 (b) provider=oci에서 ACL 항목 "필요 없음" (c) `DISABLE_DATA_ACCESS` 상태 만들고 점검 | (a) 적용 후 전 항목 통과, 적용 전 SQL 미리보기 표시 (b) ACL 자동 통과 (c) Data Access 항목 적색 → 원클릭 ENABLE 후 녹색, narrate 정상화 |
| QA-04 | FR-04 | 21개 검증 속성 폼 전수 렌더링 + 해설 존재 검사(자동화) / 폼 입력→CREATE_PROFILE 미리보기 SQL과 실제 실행 SQL 동일성 | 해설 커버리지 100%, 미리보기=실행 SQL 일치, 미검증 속성은 "고급 JSON" 영역에서만 입력 가능 |
| QA-05 | FR-05 | 프로파일 CRUD + 기본 프로파일 지정 후 **앱 재시작** → 액션/챗봇 화면 자동 적용 확인 / 속성 상세가 `USER_CLOUD_AI_PROFILE_ATTRIBUTES` 값과 일치 | 기본 프로파일이 앱 설정에 영속(DB 세션 의존 없음), 액션 선택지/실행 경로에 "showparameter" 문자열 부재. 단, PG-03b의 학습 메모처럼 존재하지 않는 액션임을 설명하는 정적 문구는 허용 |
| QA-06 | FR-06 | 동일 프롬프트로 P0 5개 액션 전환 실행 / 작은따옴표 포함 프롬프트(`don't`) / 실패 유도 프롬프트 | 5개 액션 모두 응답+latency 표시, 실행 SQL 펼침에 `DBMS_CLOUD_AI.GENERATE` 원문 노출, `''` 이스케이프 확인, 실패 시 오류 원문+한국어 해설+재시도 버튼 |
| QA-07 | FR-07 | 새 대화 생성→멀티턴 3회→맥락 비교 모드→이력 조회→DROP_CONVERSATION / 백엔드 워커 2개 이상 환경에서 멀티턴(stateless 검증 핵심) | conversation_id가 매 GENERATE params에 포함(SQL 펼침으로 검증), **서로 다른 DB 세션/워커를 거쳐도 맥락 유지**, 비교 모드 좌우 응답 상이 |
| QA-08 | FR-08 | 스키마 원클릭 생성→comments off 실행→COMMENT 일괄 적용→comments on 실행→좌우 비교 / 초기화 후 반복 2회 | 전/후 SQL이 좌우에 표시되고 후 SQL이 c7 등 의도 컬럼 사용(리허설 수동 확인), 초기화가 COMMENT까지 제거해 반복 시연 가능, DDL 미리보기=실행 DDL 일치 |
| QA-09 | 횡단 | 세션 상태 금지 정적 검사: 백엔드 코드에 `SET_PROFILE`/`SET_CONVERSATION_ID`/`'SELECT AI'` 키워드 사용 부재 (코드 리뷰 + grep CI) | 검출 0건 (PRD 리스크 R3 완화 검증) |
| QA-10 | 횡단 | 보안 최소선: 서버 저장 파일/로그 전수에서 admin 비밀번호·wallet 비밀번호 평문 탐색 | 검출 0건 |

### 6.2 시나리오 기반 E2E (페르소나 수용 테스트)

| ID | 페르소나 | 시나리오 | 합격 기준 (PRD §7 지표 연동) |
|---|---|---|---|
| E2E-1 | P1 Presales | §1 표준 20분 시나리오 신규 환경 완주 | wallet 업로드→첫 NL2SQL 응답 15분 이내, 수작업 SQL 0건 |
| E2E-2 | P2 영업 대표 | §2 단축 5분 시나리오를 매뉴얼 없이 완주 (실사용자 테스트 5인) | 완주율 80% 이상, 타이핑 0회 |
| E2E-3 | P3 파트너 | 표준 시나리오 중 "실행 SQL 보기"만으로 GENERATE 패턴·CREATE_PROFILE 구문을 재구성할 수 있는지 인터뷰 검증 | 핵심 호출 패턴 3개(GENERATE/CREATE_PROFILE/CREATE_CONVERSATION) 식별 성공 |
| E2E-4 | 오류 복구 | §5.3 오류 표 중 ORA-20000·credential·모델 오류 3종을 의도적으로 주입 | 화면 안내만으로 복구(자가 복구율 측정), 막힌 단계에서 다음 단계 진입 가드 동작 |

### 6.3 QA 일정 권고

1. **MVP 코드 프리즈 전**: QA-01~10 자동화 가능 항목(구조 검증) CI 편입, QA-09 grep 검사는 PR 게이트로 즉시 적용.
2. **MVP 릴리스 전**: E2E-1, E2E-4 필수 통과. LLM 내용 검증(QA-06/08의 정답성)은 리허설 체크리스트 §5.1 전수 실행으로 갈음하고 결과를 기록.
3. **v1.1 전**: showprompt/feedback 추가 시 FR-03의 `V_$MAPPED_SQL`/`V_$SESSION` READ grant 점검 항목을 QA-03에 확장.
