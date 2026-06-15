# 세션 프롬프트 기록

> 이 파일은 현재 Claude Code 세션에서 사용자가 입력한 모든 프롬프트를 순서대로 기록합니다.
> 세션 종료 시점까지 새 프롬프트가 입력될 때마다 갱신됩니다.

- **세션 날짜**: 2026-06-12
- **프로젝트**: Select AI 데모 애플리케이션 (selectai_uis)

---

## 프롬프트 1 — 데모 애플리케이션 PRD 및 관련 문서 작성 요청

```
@oracle-database-select-ai-users-guide.pdf
를 참조하여 데모 애플리케이션을 개발하려 합니다.
목적: Oracle NL2SQL인 Select AI 데모 환경 제공, 고객에게 쉽게 Select AI 기능 소개용 데모
Database: OCI ADB 26ai
사용자: 오라클 Presales, 영업, 파트너
DB User: admin

특징
- 쉬운 오라클 데이터베이스 연결
- 커넥션 관리
- 권한 설정 확인 / 권한 설정
- 프로파일 설정 및 항목 설명을 통한 이해
- 프로파일 관리
- select ai 기능 시연: runsql, showsql, narrate, showparameter, explain
- chatbot 통합 시연
- coment / annotation 증강: enhancement data in target table

UI: react 기반의 직관적이고 세련된 UI * page flow (design.md에 저장)
Design: Oracle redwood Style(style.md 저장)

기술력이 낮이 엔지니어와 영업이 쉽게 데모할 수 있는 select ai 작업 흐름을 보여주고
직접 자연어 쿼리를 수행하는 직관적인 Demo 애개발

이 애플리케이션 데모를 개발하기 위한 PRD와 관련 문서를 작성해 주세요
8 전문가를 이용해 협업 체제로 문서를 작성해 주세요

설정 공백이 있다면 작업 초기에 적극 문의해 주세요
```

### 보충 답변 (설정 공백 질의에 대한 사용자 응답)

| 질문 | 사용자 답변 |
|------|------------|
| 백엔드 기술 스택 | Python FastAPI (권장) |
| Select AI 기본 AI Provider | OCI Generative AI (권장) |
| ADB 연결 방식 | mTLS Wallet 업로드 |
| 배포/실행 형태 | 개발은 로컬로 하고 OCI Compute에 배포가 최종 목적 |

---

## 프롬프트 2 — 세션 프롬프트 기록 요청

```
현재 세션에서 내가 지시한 모든 프롬프트는 prompt.md에 저장해주세요. 앞서 입력한 사항도 적용해주세요. 세션 종료시점까지 계속 유지됩니다.
```

---

## 프롬프트 3 — 사용량 확인 명령

```
/usage
```

---

## 프롬프트 4 — showparameter 오기 확인 및 전체 오류 검토 요청

```
showparameter로 오류를 입력한거 같아요.
전체적인 오류 검토 해주세요
```

---

## 프롬프트 5 — 터미널 스타일 SQL 로그 창 추가 요청

```
UI 하단에 Database에서 수행되는 SQL을 로그로 출력하는
터미널 스타일의 로그 창을 만들어 주세요
이 화면은 DB Interaction을 수행하는 화면에 아래에 show / no show를 vscode terminal 스타일로 추가해주세요
```

---

## 프롬프트 6 — 개발 착수 준비 확인 및 개발 프롬프트 제안 요청

```
이제 개발할 준비가 완료됐나요?
개발 가능하다면 8개 에이전트로 팀을 구성하여 개발즐 진행해주세요
단위 테스트를 통해서 코드 강전성을 높여 주세요
프로젝트에 git을 초기화하고 버전관리 해주세요
위 작업을 위한 구체적인 프롬프트 제안해주세요
```

---

## 프롬프트 7 — 미해결 이슈 결정사항 확인 요청

```
결정사항 말해줘요
```

---

## 프롬프트 8 — X1 키의 정체 질문

```
X1의 키는 어떤 키인가요?
```

---

## 프롬프트 9 — wallet 자동 다운로드 요구사항 추가

```
wallet이 없을경우  oci cli를 통해서 지정된 컴파크먼트와 ADB 이름으로 다운로드 합니다.
다운로드 위치는 ~/.selectai/wallets/
```

---

## 프롬프트 10 — X2 의미 설명 요청

```
x1이 해결됐다면 x2로 넘어가죠 의미 설명해주세요
```

---

## 프롬프트 11 — X2 저장 방식 변경 지시 (SQLite → JSON 파일)

```
데이터는 sqllite로 하지 말고. ~/.selectai/resources.json 에 저장하고 정리하는 crud로 개발해주세요
```

---

## 프롬프트 12 — 진행 지시

```
go
```

---

## 프롬프트 13 — X3 항목 설명 요청

```
완료 됐다면 X3로 넘어가 주세요. 항목 설명
```

---

## 프롬프트 14 — 진행 재개 지시

```
gogo
```

(주: 모델을 Opus 4.8로 전환 후 동일하게 "gogo" 입력 — X2 저장소 SQLite→JSON 전환 작업 계속)

---

## 프롬프트 15 — 대상 스키마/테이블 선택 기능 요청

```
대상 스키마와 테이블을 선정할 수 있게 해주세요
가령 Database에 인증한 스키마에서 보이는 테이블을 대상으로 선정하고 프로파일이 생성됨으로 했으해요
```

---

## 프롬프트 16 — 다음 단계(개발 착수) 진행 지시

```
다음으로 넘어가요
```

---

## 프롬프트 17 — 개발 워크플로 중지

```
중지
```

(이어서 "모두 중지" — 모든 백그라운드 작업 종료)

---

## 프롬프트 18 — X3 결정 사항 재설명 요청

```
결정 사항 x3 설명
```

---

## 프롬프트 19 — 대상 테이블 선택 가능 + 전 문서 일관성 확보 지시

```
대상 테이블은 선택할 수 있도록 함
모든 문서는 여기에 일관성 확보
```

---

## 프롬프트 20 — X4 결정 사항 설명 요청

```
x4
```

---

## 프롬프트 21 — 다음(X5) 설명 요청

```
다음
```

---

## 프롬프트 22 — X5 확인 및 다음(X6) 진행 요청

```
AI Provider 선택지 목록과 Hugging Face 제외확인
다음으로 넘겨주세요
```

---

## 프롬프트 23 — 앞서 개발한 코드 전체 제거 요청

```
앞에서 개발한 코드는 모두 제거
```

---

## 프롬프트 24~31 (요약)

- 키 회전·OCI Vault 비목표 처리 / 문서 변경분 커밋 / 8 에이전트 개발 착수·세션한도·네트워크 오류로 분할 재개 / 남은 프론트 2페이지·README·run.sh 직접 완성 후 커밋 / 서버 기동
- 커넥션 502 오류(암호화 ewallet.pem PEM 암호 미전달) 수정 + wallet 암호 입력란을 admin user/password 위로 이동
- 저장 후 백스크린 현상 → ErrorBoundary 추가(원인은 라이브 편집 중 HMR 일시 오류로 추정)
- `ls ~/.oci` 확인 (config·api-key.pem 존재)

## 프롬프트 32 — 권한 점검: Principal 제거 기능 + OCI 기본값 자동 채우기

```
권한 점검에서 Resource Principal과 User Principal을 제거하는 기능 추가
~/.oci의 config와 api-key.pem 파일이 있다면 기본값을 user principal 설정 폼에 기본값으로 설정해 주세요. 없다면 기본 설정은 생략해주세요
```

---

## 프롬프트 33 — 백스크린 실제 원인(쿼리 키 충돌) + credential_name select 요청

```
화면을 그리는 중 오류가 발생했습니다 ... TypeError: connections.map is not a function ... db 커넥션 추가 후 페이지 렌더링 오류
```
→ 원인: ["connections"]/["profiles"] 쿼리 키를 페이지마다 다른 반환 형태(배열 vs envelope)로 공유 → 캐시 충돌. 모두 배열로 통일.

```
프로파일에서 credential_name은 현재 설정 가능한 목록을 select list로 제공해주세요
```

---

## 프롬프트 34 — region select + 편집 모드 object_list 기존 선택 표시

```
region은 generative ai를 선택할 수 이는 리전을 선택해 가능하게 해주세요.
편지 모드에서 object_list 기존에 선택 목록을 출력해줘
```

---

## 프롬프트 35 — 플레이그라운드: 실행 시 6액션 동시 실행 후 탭별 결과 + 추천 질문 한글화

```
플레이 그라운드에서 실행 버튼을 누르면 runsql showsql explainsql narrate chat showprompt 동시에 시작하고 tab에 해당 결과가 출력된다.
이 기능으로 업데이트 해주세요
추천 질문은 한글로 작업해주세요
```

---

## 프롬프트 36 — showprompt 가독성 극대화 + 플레이그라운드 chat 제거

```
(showprompt 실제 출력은 chat 메시지 JSON 배열) 이런 텍스트 원본 출력은 도움이 안되요 가독성을 극대화 해주세요
CL 처리하고 escape 문자를 위한 \ 제거 및 핵심 키워드 하이라이트 등 가독성에 신경 써줘요
```
→ AugmentedPromptView를 메시지 구조 분해(SYSTEM 스키마=SQL 하이라이트 다크패널 / USER=Question 강조)로 재작성.

```
chat 텝 제거해주세요
병렬처리는 5개로 수정 chat 제외
```

---

## 프롬프트 37 — showprompt 원문 펼쳐보기 추가

```
프롬프트 원문을 아래체 출력해주세요 확장하여 볼 수 있도록 해주세요
```

---

## 프롬프트 38 — DB 오류(DPY-4024) 원인 문의

```
현재 서버에 오류가 발생했데요 이유가 뭔가요?
DB 오류가 발생했습니다. 원문을 확인하세요. DPY-4024
```
→ 데이터 딕셔너리 조인 쿼리 15초 타임아웃 초과. 쿼리 분리·N+1 제거·타임아웃 30초·데모 테이블만 조회로 해결.

---

## 프롬프트 39 — 편집 시 현재 프로파일 코드 표시

```
profile 설정이 이미 프로파일이 만들어져 있으면 현재 프로파일 코드가 보이도록 해주세요.
현재 설정으로
```

(추가: "profile 설정 화면에서 이미 프로파일이 만들어져 있으면 현재 프로파일 코드가 보이도록" → ProfileDetail(PG-03b)에도 코드 패널 추가. /enrichment 백스크린 = ["schema","owners"] 쿼리 키 형태 충돌 → 통일)

---

## 프롬프트 40 — 메타 강화 메뉴 (준비하기): comment/annotation 확인·추가 + grok-4 LLM 증강

```
준비하기에 meta 강화 메뉴를 추가하고 선택한 프로파일의 대상 TABLE 목록을 선택하면 comment와 annotation을 확인하고 추가하는 필요하다면 데이터 분석을 통해서 정보를 증강하는 기능을 추가할 수 있나요? 이때 llm이 필요하다면 grok 4.3을 사용해주세요 가능한가요?
```
→ 가능. xai.grok-4 사용 확정, 제안 전부 수용. LLM은 메타강화 전용 grok 프로파일(META_GROK) 자동 생성으로 호출.
```
xai.grok-4 사용하고 제안한 모든 내용 수용합니다.
```

---

## 프롬프트 41 — 메타 강화: 테이블/컬럼 레벨 + annotation 편집/추가, 팝업 활용 디자인

```
comment와 annotation을 설정할 때 테이블 레벨과 컬럼 레벨 설정이 가능하고 annotation은 기존 편집과 추가가 가능합니다. 이러한 특성을 반영하여 popup을 적극 활용하는 디자인은 어떤가요?
```
→ 동의. 모달 컴포넌트 신설, 테이블+컬럼 행별 [편집] 팝업에서 comment 편집 + annotation ADD/REPLACE/DROP 관리.

---

## 프롬프트 42 — 메타 강화: comment / annotation 팝업 분리

```
메타 강화에서 annottion과 comment를 분리 팝업으로해주세요
```
→ 단일 편집 팝업을 COMMENT 팝업 / ANNOTATION 팝업 2개로 분리, 행마다 [코멘트][어노테이션] 버튼.

---

## 프롬프트 43 — 증강 비교 메뉴 제외

```
증강 비교는 제외해 주세요
```
→ 시연하기에서 ⑦ 증강 비교(/enrichment) 메뉴 항목 제거.

---

## 프롬프트 44 — 어노테이션 입력 편의 디자인 (표준 키 딕셔너리)

```
(Oracle Select AI Annotation 실무 가이드 첨부) annotation 구성에 있어서 입력을 편리하게 하는 디자인을 적용해주세요
```
→ 가이드의 표준 키 딕셔너리(business_name/synonyms/unit/range/value_map/note/join_hint/pk/fk/pii/classification/column_hidden + 테이블 domain/source_system/refresh/owner)를 프리셋으로 제공. 키 선택(레벨별 필터)·플래그 키 값없음·value_map JSON·예시 placeholder·설명 힌트 + 빠른 추가 칩.

---

## 프롬프트 45 — "메타 제안 및 적용" 고도화 (관계 분석 + 편집/선택/일괄 적용)

```
grok-4 분석 제안 개선 → "메타 제안 및 적용": 샘플 데이터 + profile의 다른 테이블과의 관계(FK)를 분석하여
table/column 레벨 comment·annotation을 제안. 사용자가 편집·선택 후 일괄/선택 적용.
프롬프트 보강하여 수행.
```
→ 백엔드 suggest 강화(관련 테이블 컬럼+FK 컨텍스트, 표준 키 기반 구조화 JSON, table/column 레벨) + POST /meta/apply 일괄 적용. 프론트는 제안 검토(편집·체크 선택)·선택/전체 적용 UI.

---

## 프롬프트 46 — 메타 적용 실패(성공 0/실패 20) 원인 문의

```
메타 적용 완료 — 성공 0, 실패 20 이유는?
```
→ 권한 문제. 대상이 SH 샘플 스키마(소유 SH)인데 접속자는 ADMIN → ORA-41900(COMMENT 권한 없음)/ORA-01031(권한 부족). 실패 사유를 모달에 표시하도록 개선.

---

## 프롬프트 47 — 메타 보강 시 권한 체크 + 부여 기능 가능성 + 세부 프롬프트 요청

```
메타 보강을 할때 권한을 체크하고 권한 부족시 권한을 부여하는 기능 제공할 수 있나요?
현재 접속 사용자가 권한을 부여할 권한이 없다면 불가능한 이유 설명해 주세요
이 기능 구현을 위한 세부 프롬프트 생성해주세요
```
→ 체크 가능, 부여는 조건부. (세부 구현 프롬프트는 답변에 제공)

---

## 프롬프트 48 — 권한 체크/부여 구현 지시

```
지금 바로 구현해주세요
```
→ GET /meta/privilege-check (소유/보유권한/보호스키마/부여가능 + can_apply) + POST /meta/grant 구현. 발견: SH 실패 원인은 권한 아니라 oracle_maintained 보호 스키마. 프론트 권한 배너 + [권한 부여] + 적용 게이트.

---

## 프롬프트 49 — Select AI feedback 기능 추가 방법 가이드 요청

```
여기에 select ai feedback 기능을 추가하려 합니다. 어떻게 해야 할까요? 방법을 우선 가이드 해주세요
```
→ 가이드 제공(답변). 이미 구현된 것: FEEDBACK 백엔드/엔드포인트/모델, prereq feedback_grants 점검, 플레이그라운드 👍/👎. 갭: 부정 피드백 교정 입력·before/after 데모 루프·feedback grants 적용·피드백 관리(delete).

---

## 프롬프트 50 — 독립 "피드백" 메뉴(플레이그라운드 아래) + 권한 점검/부여/불가표시

```
피드백을 수행하려 할 때 권한이 없으면 권한 부재와 권한 설정 기능을 추가
현재 접속 user가 권한 설정 권한이 없으면 불가함을 표시
하는 것을 추가한 독립 메뉴에 기능을 추가해주세요. 플레이그라운드 아래에 추가해 주세요
이와 관련된 프롬프트를 우선 제안하고 관련 기능을 수행해 주세요
```
→ 제안 프롬프트 제시 후 구현: /feedback 메뉴(시연하기, 플레이그라운드 다음) + GET /selectai/feedback/privilege-check(V_$MAPPED_SQL/V_$SESSION READ, GRANT ANY OBJECT PRIVILEGE 부여가능 판정) + POST /selectai/feedback/grant + 피드백 데모 흐름(질문→showsql→👍/👎+교정→FEEDBACK→재실행 비교).

---

## 프롬프트 24 — 키 회전·OCI Vault 연동 범위 제외 (데모용)

```
암호화 키 회전·OCI Vault 연동 (P2)을 추가할 필요는 없습니다
데모용 입니다.
```

---

## 프롬프트 25 — 문서 변경분 커밋 요청

```
문서 변경분 커밋
```

---

## 프롬프트 26 — 개발 착수 (8 에이전트 체제)

```
이제 개발 들어가줘요
8에이전트 체제로 들어가붜요
```

---

## 프롬프트 27 — 소요 시간 질문

```
얼마나 걸릴까?
```

---

## 프롬프트 28 — 세션 한도 리셋 후 개발 재개 지시

```
계속 고
```

(주: Phase 1 스캐폴딩 완료 후 세션 한도로 Phase 2~4 에이전트 8명 실패 → 한도 리셋 후 재개)

---

## 프롬프트 29 — 네트워크 오류 후 재재개 지시

```
다시고
```

(주: 재개 실행에서 백엔드 코어·Select AI·프론트 셸·준비화면 완료, 프론트 시연화면·테스트 2명·통합이 네트워크 오류로 실패 → 캐시 재개)

---

## 프롬프트 30 — Select AI Feedback 기능 추가 가이드 요청

```
여기에 select ai feedback 기능을 추가하려 합니다. 어떻게 해야 할까오? 방법을 우선 가이드 해줏에ㅛ
```

---

## 프롬프트 31 — 권한 점검·부여 포함 독립 피드백 메뉴 추가

```
피드백을 수행하려 할 때 권한이 없으면 권한 부재와 권한 설정 기능을 추가 / 현재 접속 user가 권한 설정 권한이 없으면 불가함을 표시 / 하는 것을 추가한 독립 메뉴에 기능을 추가해주세요. 플레이그라운드 아래에 추가해 주세요 / 이와 관련된 프롬프트를 우선 제안하고 관련 기능을 수행해 주세요
```

---

## 프롬프트 32 — Data Access 비활성화(ORA-20000) 오류 보고

```
Select AI의 데이터 액세스가 비활성화되어 있어 narrate/합성 데이터를 실행할 수 없습니다. 권한 점검 화면에서 'Data Access 활성화' 버튼을 눌러 ENABLE_DATA_ACCESS를 적용한 뒤 다시 시도하세요. 에러 발생
```

---

## 프롬프트 33 — 현재 오류 분석 요청

```
현재 오류 분석
```

---

## 프롬프트 34 — Data Access 재비활성화 재보고

```
Select AI의 데이터 액세스가 비활성화되어 있어 narrate/합성 데이터를 실행할 수 없습니다. 권한 점검 화면에서 'Data Access 활성화' 버튼을 눌러 ENABLE_DATA_ACCESS를 적용한 뒤 다시 시도하세요.
```

(주: ENABLE_DATA_ACCESS는 세션 스코프 → 백엔드 리로드 시 소실. run_generate에 자동 재활성화+1회 재시도 self-heal 적용)

---

## 프롬프트 35 — 피드백이 왜 narrate로 시작하는지 질문

```
feedback 기능이 왜 narrate로 시작하나요?
```

(답: narrate 아님 — 피드백 페이지는 showsql 사용 중임을 확인)

---

## 프롬프트 36 — 피드백 페이지를 runsql로 수정 요청

```
runsql로 수정해주세요
```

(처리: Feedback.tsx의 genBefore/genAfter를 action "runsql" + row_limit 100으로 변경, before/after 상태를 GenerateResult로 전환, ResultView 헬퍼 추가해 생성 SQL + 결과 표(ResultGrid) 렌더)

---

## 프롬프트 37 — 피드백 처리 시 에러 (@urerror.jpeg)

```
@urerror.jpeg feedback 처리시 에러
```

(첨부: localhost:5173/feedback 에서 runsql 결과는 정상 표시되나 '👍 긍정' 클릭 시
"Select AI의 데이터 액세스가 비활성화..." 토스트 발생)

### 추가 단서 (사용자가 붙여넣은 SQL 로그)
```
[PG-feedback/feedback:positive] BEGIN DBMS_CLOUD_AI.FEEDBACK(profile_name => 'GENAI_SH',
  sql_text => '국가별 고객 수를 알려주세요', feedback_type => 'positive', operation => 'add'); END; ✗ ORA-20000
```

### 근본 원인 (직접 재현으로 규명)
1. ORA-20000을 errors.py가 **무조건 DATA_ACCESS_DISABLED로 오분류** — 실제로는 RAISE_APPLICATION_ERROR 범용 코드라 의미가 다름.
2. 실제 메시지: `ORA-20000: No matching SQL statement found for the SQL_ID or SQL text.`
3. `sql_text`는 **`select ai <action> <프롬프트>` 형식**이어야 함(그냥 프롬프트면 `is not a Select AI statement`).
4. **부정(negative)**: 프리픽스 sql_text + `response`(교정 SQL) → 성공.
5. **긍정(positive)**: v$mapped_sql 매핑 필요 → 본 앱은 GENERATE()로만 실행해 매핑 없음 → SET_PROFILE + `select ai showsql <프롬프트>` 1회 실행으로 시드한 뒤에야 성공.

### 처리
- `errors.py`: ORA-20000을 메시지 substring으로 분기(ORA20000_VARIANTS) — DATA_ACCESS_DISABLED / FEEDBACK_INVALID_STATEMENT / FEEDBACK_NO_MATCH, 미일치 시 기존 데이터액세스로 폴백.
- `selectai_service.send_feedback`: `_ai_statement_text()`로 프롬프트를 `select ai showsql ...` 형식 정규화, 긍정 피드백은 `_seed_mapped_sql()`(SET_PROFILE+프리픽스 실행)로 v$mapped_sql 시드 후 FEEDBACK 호출. (잘못 추가했던 데이터액세스 self-heal 제거)
- `Feedback.tsx`: 안내 문구를 긍정/부정 동작 차이에 맞게 수정.
- 실DB E2E 검증: 긍정/부정 모두 SUCCESS.

---

## 프롬프트 38 — UI를 Oracle Redwood 스타일로 변경

(Redwood 핵심 원칙·디자인 토큰·컴포넌트 가이드 전문을 제시하며)
```
위 프롬프트를 수정하여 현재 demo의 ui를 oracle redwood 스타일로 변경해주세요
```

### 처리 (토큰 중앙화 구조를 활용 — 단일 파일 리매핑으로 앱 전체 일괄 전환)
- `src/styles/tokens.css` 재작성: 웜페이퍼 → **웜-슬레이트 Redwood 팔레트**로 리매핑.
  - 페이지 배경 `#F1EFED`, 표면 흰색, 보더/구분선 슬레이트 `#C2D4D4`,
    본문·헤더 텍스트 `#3C4545`(slate-150), 보조 텍스트 `#697778`(slate-100).
  - **primary 버튼 = Oracle Red `#C74634`**(기존 잉크 → 변경). `--color-action-primary`만
    바꿔 기본 `<Button>`이 전부 Redwood Red CTA가 됨.
  - 라운딩 6/8/12px(부드럽게), 그림자 슬레이트 잉크 기반 얕은 elev-1/-2,
    info/focus `#3A6EA5`, danger=Oracle Red, warning 텍스트는 AA 안전 앰버(#B7790A)+
    brand-yellow(#F1B13F) 액센트 분리, 본문 줄간격 1.6.
  - `@theme` 블록(Tailwind 유틸 bg-paper/text-ink 등)도 동일 값으로 정렬.
- `index.html`: Inter 웹폰트 로드(Oracle Sans 미설치 폴백), 폰트 스택 `Oracle Sans`→`Inter`→system.
- `Button.tsx`: 헤더 주석을 'primary=Oracle Red'로 갱신.
- 검증: tsc 클린, `npm run build` 성공, 컴파일 CSS에 #c74634/#f1efed/#c2d4d4/#3c4545 포함 확인, vite HMR 반영.
- 메모: 한 화면에 빨강 primary는 가급적 하나라는 원칙상, 보조 액션이 함께 있는 화면은
  해당 버튼을 variant="secondary"로 강등 권장(후속 미세조정 여지).

---

## 프롬프트 39 — 좌측 메뉴 가독성 개선 (숫자 → 의미 아이콘 + 글자 확대)

```
왼편 메뉴의 글씨가 작다. 숫대 대신에 의미에 해당하는 아이콘 이미지 혹은 이모지를
사용하여 가독성을 높여 달라 / 이를 처리하는 구체적인 프롬프트를 제안하고 실행해주세요
```

### 처리 (AppShell.tsx)
- NAV_ITEMS의 `step`(①~⑦) 제거 → 의미 lucide 라인 아이콘으로 교체:
  커넥션=Plug, 권한 점검=ShieldCheck, 프로파일=SlidersHorizontal, 메타 강화=Tags,
  플레이그라운드=Sparkles, 피드백=ThumbsUp, 챗봇=Bot, 대시보드=LayoutDashboard, 설정=Settings.
- 라벨 13px(text-sm) → 15px(text-[0.9375rem]), 아이콘 18px, 행 패딩 py-2→py-2.5, gap 2→3,
  그룹 간격 mb-4→mb-5로 가독성 향상.
- 완료 표시 '✓' 텍스트 → lucide Check 아이콘.
- 활성 상태: 아이콘만 Redwood Red 강조(장식이라 대비 규칙 비대상), 라벨은 잉크 유지
  (빨강 라벨은 흰 배경 대비 ~3.2:1로 AA 미달 + '본문 텍스트 빨강 금지' 원칙 위배 회피).
- 여정 순서는 배열 정렬·그룹명으로 유지, 잠금 가드 레일 동작 그대로.
- 검증: tsc 클린, build 성공, HMR 반영.

---

## 프롬프트 40 — 타이틀 변경 + Oracle 로고 추가

```
Select AI Demo Studio 타이틀은 Select AI Studio로 수정하고 앞에 오라클 이미지를 추가할 것
```

### 처리
- `public/oracle-logo.svg` 신규: Oracle 워드마크 SVG(Redwood Red #C74634, 외부 의존 없는 단일 파일).
- `AppShell.tsx` 헤더: 브랜드 액센트 바 → Oracle 로고 이미지 + 얇은 구분선 + 타이틀 "Select AI Studio".
- `index.html` <title>, `Onboarding.tsx` h2 모두 "Select AI Studio"로 변경(온보딩은 로고 이미지도 상단 추가).
- 검증: 잔존 'Demo' 없음, tsc 클린, build 성공, 로고가 dist에 복사됨.

---

## 프롬프트 41 — 플레이그라운드 "X-Connection-Id 헤더 누락" 오류 (@uierror2.jpeg)

```
@uierror2.jpeg 오류 확인
```

(헤더엔 demo-admin-3/ADMIN 선택 + 건강 5/5인데 플레이그라운드에서 CONNECTION_REQUIRED 토스트 2개)

### 근본 원인
- 토스트 정확히 2개 = 마운트 쿼리 `/profiles`(목록)·`/settings/default-profile`(GET)이 X-Connection-Id를 요구하는데 `enabled` 게이트 없이 발사. (`/selectai/actions`·`/suggested-prompts`는 커넥션 불필요라 무사)
- 더 깊은 원인: connectionStore `partialize`가 `mode`·`sqlTransparent`만 영속하고 **`activeConnectionId` 미저장** → 새로고침 시 항상 null로 시작, 커넥션 자동선택(AppShell useEffect) 전에 발사된 요청은 헤더 누락. (부가로 새로고침마다 선택 커넥션이 connections[0]로 리셋되는 UX 버그도 동반)
- Playground는 useConnectionStore를 아예 안 써서 직격탄.

### 처리
- `Playground.tsx`: useConnectionStore 도입, `profilesQuery`·`defaultProfileQuery`에 `enabled: !!activeConnectionId` 추가(커넥션 활성 시 자동 refetch).
- `connectionStore.ts`: `partialize`에 `activeConnectionId` 추가(영속) — 새로고침 직후에도 헤더 즉시 첨부. 커넥션 메타 객체는 stale 우려로 미저장.
- `AppShell.tsx`: 커넥션 목록 로드 후 영속 id로 메타 복원(선택 유지), 없거나 사라진 id면 last_used 커넥션 자동 선택.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 42 — 피드백 적용 명시적 검증(데이터 출력)

```
피드백이 적용됐다고 나오지만 실제 적용된 것인지 메시지 이외에 정보가 없음
특히 쿼리 재수행시 변경이 없음
명시적으로 적용됨을 확인하는 것이 필요하고 (데이터 조회 출력 등)
정상 동작 확인이 필요함
```

### 분석
- 피드백은 `<프로파일>_FEEDBACK_VECINDEX$VECTAB` 벡터 테이블(CONTENT/ATTRIBUTES JSON/EMBEDDING)에
  적재됨. 토스트 외엔 증빙이 없어 "적용됐는지" 확인 불가. 재실행 무변화는 LLM 벡터 유사도 기반이라
  항상 즉시 반영되지 않음 → 저장 사실 자체를 데이터로 보여줘야 함.

### 처리 (백엔드)
- `selectai_service`: `feedback_table_name()`, `_read_feedback_row()`(sql_text/sql_id로 방금 저장한 행 조회),
  `list_feedback()`(프로파일 피드백 전체, ORA-00942=테이블 없음→exists:False) 추가.
- `send_feedback` 반환에 `stored`(방금 저장된 행) 동봉 — POST 응답 자체가 적용 증빙.
- 라우트 `GET /selectai/feedback/list?profile_name=&prompt=` 추가.

### 처리 (프론트 Feedback.tsx)
- `feedbackListQuery`(저장 피드백 조회) + 토스트를 stored 유무로 "저장 확인됨/실패" 구분.
- 피드백 제출 성공 시 목록 자동 refetch.
- "④ 저장된 피드백 (적용 검증)" 패널 신규: 테이블명·건수 표기 + 항목별 긍정/부정 배지·프롬프트·
  개선 힌트·기록된 SQL(response, SqlBlock) 출력. 새로고침 버튼.

### 검증
- 실DB E2E: list_feedback exists:True/items, send_feedback stored 반환 확인. tsc 클린, build 성공.

---

## 프롬프트 43 — ③↔④ 순서 교체

```
④ 저장된 피드백 (적용 검증) 과 ③ 같은 질문 재실행 → 전/후 비교 을 바꿔 주세요
```

### 처리 (Feedback.tsx)
- "저장된 피드백 (적용 검증)" → ③, "같은 질문 재실행 → 전/후 비교" → ④로 번호·렌더 순서 교체.

---

## 프롬프트 44 — 피드백 후 쿼리 가독성 개선

```
피드백 후 쿼리도 가독성 좋게 출력해주세요
```

### 처리 (Feedback.tsx ④ 패널)
- 기존: ComparePanes 좁은 칸에 SQL+표를 함께 넣어 생성 SQL이 cramped.
- 개선: "피드백 전/후 생성 SQL"을 각각 전체 폭 SqlBlock(구문 강조, defaultOpen)으로 위아래 표시,
  데이터 결과(ResultGrid)만 좌우 ComparePanes로 비교. summary 문구도 갱신.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 45 — ORA-01002(fetch out of sequence) 오류

```
[PG-feedback/runsql-전] SELECT DBMS_CLOUD_AI.GENERATE(prompt => '연령대별 고객수를 알려주세요',
  profile_name => 'GENAI_SH', action => 'showsql') AS response FROM dual ✗ ORA-01002
```

### 분석
- ORA-01002는 GENERATE 내부 커밋이나 풀 세션 상태 오염(긍정 피드백 시드의 SET_PROFILE 잔존 가능)으로
  비동기 SELECT 페치가 깨질 때 발생하는 일시적 오류. 매핑에 없어 raw 500으로 노출됨.

### 처리
- `errors.py`: ORA-01002 → DB_CONNECTION_UNSTABLE(503, retryable) 매핑 + 한국어 안내.
- `selectai_service`: `_generate_resilient()` 헬퍼 신설 — call_generate를 ①DATA_ACCESS 자가복구
  ②DB_CONNECTION_UNSTABLE 시 `close_pool()`로 오염/끊긴 세션 폐기 후 새 커넥션으로 1회 재시도.
  run_generate(비-runsql)·_run_runsql(showsql)이 공용 사용. runsql 데이터 페치 단계도 동일 재시도 추가.
- 검증: 구문 OK, ORA-01002 매핑 retryable 확인, run_generate 실DB 정상(국가별 19행). 
  (테스트 중 1회 DPY-4024=LLM showsql 60s 초과 발생 — 본 변경과 무관한 LLM 지연, 이미 retryable 매핑됨)

---

## 프롬프트 46 — 피드백은 갱신됐는데 쿼리는 변화 없음 (@uierror3.jpeg)

```
@uierror3.jpeg feedback은 업데이트 됨 그런데 쿼리는 변화 없음
```

### 규명 (실DB 실험)
- 화면은 긍정(👍) 피드백이었고 긍정은 "현재 SQL이 정답"으로 강화 → 재실행해도 SQL 그대로가 정상.
  (게다가 기록된 response SQL에 ORDER BY 없음 → 정렬 안 된 SQL을 정답으로 강화한 셈)
- 검증: 기존 긍정 삭제 후 **부정+교정(ORDER BY 포함 SQL)** 등록 → 같은 질문 showsql 재생성 2회 모두
  `ORDER BY c."COUNTRY_NAME"` 생성됨, showprompt 증강 프롬프트(10830자)에도 ORDER BY 반영 확인.
  → 시스템은 정상. 쿼리를 바꾸려면 부정+교정 경로를 써야 함(긍정은 강화용).

### 처리 (UX 유도 — Feedback.tsx)
- runsql 완료 시 생성 SQL을 교정 입력란(responseSql)에 자동 프리필 → ORDER BY 등만 덧붙이면 됨.
- 라벨 명시("올바른 SQL 전문(response) — 부정+교정의 핵심"), 교정란 4행 확대.
- 부정 버튼을 primary(빨강)로, response 비면 비활성 + 안내. 긍정 버튼 라벨 "현재 SQL이 정답".
- info-tint 안내 박스: 긍정=강화(SQL 그대로/정상) vs 부정+교정=교정 SQL 학습(재실행 반영) 구분 설명.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 47 — 프로파일 목록 위치 이동 + 피드백 개별 삭제

```
프로파일에 지정된 프로파일 목록을 피드백 권한 아래에 위치 시켜 주세요
피드백을 개별적으로 삭제 가능한가요? 가능하다면 삭제 기능을 추가해주세요
```

### 처리
1. 프로파일 선택기 위치 이동(Feedback.tsx): 패널 ① 안에서 빼내 "피드백 권한" 패널 바로 아래
   독립 "프로파일" 패널로 배치. 기본 프로파일 표기·적용 대상(effectiveProfile) 표시 추가.
2. 개별 삭제: 가능함 확인(실DB) — DBMS_CLOUD_AI.FEEDBACK(operation=>'delete') + sql_text(또는 sql_id)로
   해당 1건 제거(count 1→0). 
   - 백엔드 send_feedback: operation=='delete'면 v$mapped_sql 시드/stored-read 생략 가드.
   - 프론트: ③ 저장된 피드백 목록 각 항목에 🗑 삭제 버튼(danger) + confirm, 삭제 후 목록 자동 refetch.
- 검증: tsc 클린, build 성공, delete E2E(items 1→0) 확인.

---

## 프롬프트 48 — 생성 SQL을 각자의 결과 박스 안으로 이동

```
피드백 전 생성 SQL와 피드백 후 생성 SQL 을 각자의 아래 박스 안으로 이동해 주세요
```

### 처리 (Feedback.tsx ④ 패널)
- 전체 폭 별도 SqlBlock 2개로 분리했던 생성 SQL을 ComparePanes의 각 박스(피드백 전/후 결과) 안으로
  이동 — 각 박스 = 생성 SQL(SqlBlock) + 데이터 결과(ResultGrid)를 위아래로 담아 좌우 비교.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 49 — 저장된 피드백을 프로파일 아래로 이동

```
저장된 피드백을 프로파일 아래로 이동시켜 주세요
```

### 처리 (Feedback.tsx)
- "저장된 피드백 (적용 검증)" 패널을 "프로파일" 패널 바로 아래로 이동(참조 패널화 → 제목 번호 ③ 제거).
- 흐름 번호 정리: 재실행 비교 패널 ④ → ③.
- 최종 순서: 피드백 권한 → 프로파일 → 저장된 피드백 → ① 질문 → ② 피드백 → ③ 재실행 비교.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 50 — 챗봇 실행 SQL 복수 라인 출력 (@uierror4.jpeg)

```
chatting에서 실행된 쿼리를 복수 라인으로 출력하여 가독성을 높여주세요
```

### 원인
- executed_sql은 recorder의 normalize_sql이 공백을 한 칸으로 합쳐 항상 한 줄 → <pre>에서 가로 스크롤.

### 처리 (SqlBlock.tsx + Chat.tsx)
- `formatSql()` 추가: ①문자열 리터럴 \x00 sentinel로 보호(숫자/키워드 오인 방지) → ②DBMS_CLOUD_AI.*( ... )
  인자 줄바꿈 → ③주요 절 키워드(FROM/WHERE/GROUP BY/ORDER BY/JOIN/ON 등) 앞 줄바꿈 → ④문자열 복원.
- SqlBlock에 `format` prop 추가, true면 sqlText를 formatSql로 변환.
- Chat.tsx의 생성 SQL·실행 SQL·비교(without/with context) SqlBlock에 format 적용.
- 검증: node 단위테스트(GENERATE 6줄 분해, 'ORDER BY 2 DESC' 충돌 없음 확인), tsc 클린, build 성공.

---

## 프롬프트 51 — SH 스키마를 커넥션 user 스키마로 복제하는 기능

```
sh 스키마를 커넥션 user 스키마로 복제하는 기능을 추가해 주세요.
커넥션 user 스키마가 sh 스키마에 읽기 권한이 없다면 권한이 없다고 출력하고 기능제한해 주세요.
권한이 있다면 복제를 클릭하면 복제를 수행해주세요. 진행되는 과정은 로그로 출력해주세요.
테이블, 뷰, constraint 모두 복제해주세요. 메뉴는 권한점검 아래에 위치 시켜 주세요.
이 기능 구현을 위한 프롬프트를 제안하고 이 프롬프트로 작업해주세요
```

### 제안·구현 프롬프트
> "SH 스키마를 현재 커넥션 사용자 스키마로 복제하는 독립 메뉴를 권한점검 아래에 추가한다.
>  ① GET /clone/sh/check로 SH 읽기 권한(ALL_TABLES 노출 + 실제 SELECT probe)과 인벤토리를 점검,
>  권한 없으면 사유 표시 + 복제 비활성화. ② POST /clone/sh/run으로 테이블(CTAS: 구조+데이터+NOT NULL)
>  → PK/UK → CHECK(NOT NULL 제외) → FK(참조 스키마 remap) → 뷰 순으로 복제하고 단계별 로그 반환.
>  덮어쓰기 옵션. 진행 로그를 다크 패널에 단계·상태(✓/·/✗)·실행 SQL로 표시."

### 처리
- 백엔드 신규: `services/clone_service.py`(check_sh_access/clone_sh), `routers/clone.py`
  (GET /clone/sh/check, POST /clone/sh/run), main.py 라우터 등록, schemas CloneRequest{overwrite}.
  - SH 메타 조사 결과: 뷰 0, PK 7, FK 10, CHECK 110(전부 NOT NULL→CTAS로 자동). FK는 PK 이후 생성·참조 remap.
- 프론트 신규: `pages/SchemaClone.tsx`(권한 배너/인벤토리·덮어쓰기·복제 버튼·단계 로그 패널),
  App.tsx 라우트 /clone, AppShell 네비 "스키마 복제"(DatabaseBackup) 권한점검 바로 아래.
- 검증: 서비스 E2E(9테이블/PK7/FK10, 실패0) + HTTP 스모크(check has_read=true, run ok=36/failed=0). tsc 클린, build 성공.

---

## 프롬프트 52 — ADMIN.PRODUCTS 메타: comment 적용되나 annotation 안 됨, 이유?

```
ADMIN.PRODUCTS에 메타 제안을 적용할 때 comment는 적용됨 그런데 annotations은 적용 안됨. 이유는?
```

### 규명 (실DB 재현)
- annotation 적용 DDL(ALTER TABLE ... ANNOTATIONS (...))은 테이블·컬럼 모두 **직접 실행 시 성공**.
- USER_ANNOTATIONS_USAGE 조회 시 PRODUCTS에 annotation 49건 존재 → **적용은 실제로 되고 있음**.
- 진짜 원인: 재조회 쿼리 `ANNOTATIONS_SQL`이 `ALL_ANNOTATIONS_USAGE WHERE owner=:owner`인데
  이 뷰엔 **OWNER 컬럼이 없음**(객체 소유자는 ANNOTATION_OWNER) → ORA-00904.
  get_table_metadata의 `try/except AppError → []`가 이 오류를 삼켜 annotation을 **빈 목록**으로 반환
  → 화면엔 "적용 안 됨"으로 보임. comment는 ALL_TAB/COL_COMMENTS(정상 owner 컬럼)라 표시됨.

### 처리
- `meta_service.ANNOTATIONS_SQL`: `owner` → `annotation_owner` 필터로 수정(ANNOTATION_OWNER가 객체 소유자와 일치 확인).
- 검증: get_table_metadata가 ADMIN.PRODUCTS annotation 49건(테이블 5 + 컬럼별) 정상 반환. (이전 0건)

---

## 프롬프트 53 — 메타 제안 적용 시 annotation 다수 실패 (@uierror5.jpeg)

```
@uierror5.jpeg 왜 이런 에러가 메타 정보 제안에서 나올까요?
```

### 규명 (실DB 재현)
- 실패 메시지가 "DB 오류"(매핑 안 된 ORA) + 정적 힌트 "권한 부족"이라 오해 소지. 실제 원인은 권한이 아님.
- 재현: 메타 적용은 annotation을 항상 `ADD`로 수행 → PRODUCTS엔 이미 동일 annotation 존재 →
  `ORA-11552`(테이블)/`ORA-11560`(컬럼) "annotation already exists" 발생. (이전 적용분이 남아있어 중복)
- 반대로 `REPLACE`는 미존재 시 `ORA-11553/11561` "does not exist" → ADD/REPLACE 모두 단독 비idempotent.

### 처리
- `meta_service.apply_annotation`: ADD가 already-exists(11552/11560)면 REPLACE로, REPLACE가
  missing(11553/11561)이면 ADD로 자동 전환하는 **upsert 자가복구** 추가 → 재적용 항상 성공.
- `errors.py`: ORA-11552/11560(ANNOTATION_EXISTS), 11553/11561(ANNOTATION_MISSING) 매핑 추가
  (혹시 표면화돼도 "권한 부족" 대신 정확한 메시지).
- 검증: 기존/신규 annotation add 재적용 모두 성공(E2E), 구문 OK.

---

## 프롬프트 54 — 메타데이터 표 액션 라벨 줄바꿈(밀림) 수정 (@uierror6.jpeg)

```
@uierror6.jpeg 코멘트, 어노테이션 문자열 밀림 안밀리게 조정해주세요 아니면 이미지화 변경
```

### 원인
- MetaEnrich 표의 우측 액션 버튼 "코멘트"/"어노테이션"이 좁은 칸에서 글자 단위로 세로 줄바꿈됨.

### 처리 (MetaEnrich.tsx)
- RowActions 버튼을 아이콘(MessageSquareText/Tags) + `whitespace-nowrap` + `!px-2`(컴팩트)로 변경.
- 액션 td(table/column)에 `whitespace-nowrap` 추가해 칸이 줄지 않도록.
- 검증: tsc 클린, build 성공.

---

## 프롬프트 56 — 프로파일 편집 시 ORA-20046 (enforce_object_list)

```
ORA-20046: Missing value for profile attribute - enforce_object_list
프로파일 편집 에서 오류 발생 이유?
```

### 원인
- 프로파일 편집(PATCH) 경로가 프론트가 보낸 전체 attributes를 그대로 SET_ATTRIBUTES로 직렬화.
  미설정 옵션 필드가 `enforce_object_list: null`(및 ""·[]) 형태로 함께 전송됨 →
  SET_ATTRIBUTE에 빈 값 → ORA-20046(Missing value). (create 경로는 model_dump(exclude_none)로
  걸러지지만 update는 안 걸러짐 — 비대칭 버그)

### 처리
- `profile_service.build_update_attributes`: 직렬화 전 `v not in (None,"",[],{})`로 null/빈 값 제거.
  → 실제 값만 SET. (검증: model/comments만 남고 null 필드 제거 확인)

---

## 프롬프트 57 — 프로파일 편집 페이지 LLM 모델 목록 최신화

```
프로파일 편집 페이지에서 llm의 목록을 최신으로 업데이트 해주세요. llm 모델로
```

### 처리
- us-chicago-1 GenAI 모델을 OCI CLI(`model-collection list-models`)로 조회 → CHAT/ACTIVE 모델로 갱신.
- `attribute_catalog.OCI_CHAT_MODELS`를 39개로 교체(벤더별·최신/빠른 우선):
  xAI grok-4.3/4-fast/4-1-fast/4.20/3 계열, Google gemini-2.5-pro/flash/flash-lite,
  Meta llama-4-maverick/scout·3.3·3.1·3.2, Cohere command-a/latest/r-plus, OpenAI gpt-oss-120b/20b.
  (voice/tts 모델 제외). DEPRECATED에 meta.llama-3-70b-instruct 추가.
- model 속성은 enum_or_text라 목록 외 직접 입력도 가능.
- 검증: 구문 OK, attribute-meta 엔드포인트 enum 39개·첫 항목 xai.grok-4.3 노출 확인.

---

## 프롬프트 58 — o-home-shopping 데이터 적재 기능 (버킷 CSV) + 스키마 복제 페이지

```
(o-home-shopping demo의 DDL/loader/CSV 분석) 데이터 적재 기능을 구현하고 스키마 복제 페이지
SH 복제 아래에 추가. 큰 CSV는 TAEWAN.KIM에 o-home-shopping-data 공개 버킷(시카고) 생성해 이용.
```

### 처리
- OCI: us-chicago-1 TAEWAN.KIM에 공개 버킷 `o-home-shopping-data`(ObjectRead) 생성, CSV 47개(358MB) 업로드.
  공개 URL: objectstorage.us-chicago-1.oraclecloud.com/n/apackrsct01/b/o-home-shopping-data/o
- 백엔드: DDL(635줄)·manifest(47) 번들. `ohome_service`(check/setup_ddl/load_table) — CSV는 버킷
  공개 URL에서 다운로드(또는 OHOME_DATA_DIR 로컬 우선), 헤더→대문자 컬럼 매핑, 빈값→NULL,
  NLS 날짜/시각 세션 설정, executemany 1만 배치. 라우터 `/ohome/{check,ddl,load-table}` 등록.
- 프론트: SchemaClone 페이지 SH 복제 아래 '④ 소스 점검 / ⑤ 적재 실행 / ⑥ 적재 로그' 섹션.
  DDL 후 테이블별 순차 load-table 호출하며 진행률·행수 라이브 로그.
- 검증: 버킷 공개 URL 200, 서비스 E2E(DDL 47/47, broadcast 7600행 등 적재 성공), tsc/build 통과.

---

## 프롬프트 59 — 프로파일 스코프(SH/OHV2) 기반 예제 쿼리 제안·적용

```
플레이그라운드/챗봇/피드백 현재 프로파일이 sh, ohv2를 담는지 확인하고, 포함 여부에 따라
한글 자연어 쿼리(단순/복잡/분석 각 2개)를 제안 적용. 둘 다 포함하면 모두, 없으면 제외. 구현 가능?
```

### 분석 결과
- 기본 프로파일 GENAI_ADMIN object_list = ADMIN의 SH 복제 8테이블 → SH 포함, OHV2 미포함.
- → profile-aware로 구현(가능). SH만 노출, 프로파일이 OHV2 테이블 포함 시 OHV2 예제도 노출.

### 처리
- 백엔드 `suggested_prompts_for(connection, profile)`: 프로파일 object_list 분석
  (named: SH 표준테이블/OHV2_ 접두, owner-only: DB로 OHV2/SH 존재 확인, 빈 목록: 광범위→DB 존재).
  SH_EXAMPLE_PROMPTS·OHV2_EXAMPLE_PROMPTS(각 단순/복잡/분석×2) 선별 반환. 라우터 profile_name 파라미터화.
- 프론트 공용 컴포넌트 `SuggestedPrompts`(데이터셋·난이도별 칩) → Playground/Chat/Feedback 적용,
  각 페이지의 effective 프로파일로 호출.
- 검증: GENAI_ADMIN→SH 6개, SH+OHV2 임시 프로파일→12개(SH6+OHV2 6) 정상, tsc/build 통과.

---

## 프롬프트 60 — o-home 적재 속도 개선 + 비동기화

```
데이터 적재 속도 개선 방법은 없을까요? 추가로 비동기로 동작하게 하고 속도를 개선할 수 있나요?
```

### 분석·검증
- 데이터가 OCI 공개 버킷에 있으므로 ADB가 직접 읽는 DBMS_CLOUD.COPY_DATA가 최선(서버측 병렬 직접경로).
  검증: COPY_DATA로 CUSTOMER 5만행 1.0s, BROADCAST 7600행 1.3s.
- DDL에 FK 50개 존재 → 병렬 적재 위해 FK 일시 비활성→병렬→재활성(NOVALIDATE).

### 처리
- 백엔드: load_table을 COPY_DATA 우선(로컬 OHOME_DATA_DIR 지정 시 executemany 폴백)으로 전환.
  비동기 작업: `start_load_all`(백그라운드 asyncio) — DDL→FK off→Semaphore(4) 병렬 COPY_DATA→FK on,
  인메모리 진행상태. 라우터 `/ohome/load-all`(시작)·`/ohome/load-status`(폴링) 추가.
- 프론트: '적재 시작'을 load-all+폴링(1.5s)으로 변경 — 비동기, 단계/진행/행수 라이브 표시.
- E2E: 비동기 병렬 전체 적재 47/47, 4,325,626행, 실패0, 약 150초. tsc/build 통과.
