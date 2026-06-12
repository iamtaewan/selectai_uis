# Select AI Demo Studio UI Design Output

## 조사 요약

- `PRD.md`: wallet 연결, 권한 점검, 프로파일 관리, 액션 시연, 챗봇, comment 증강 비교를 P0 핵심 여정으로 정의했다.
- `design.md`: PG-00부터 PG-08까지의 정보 구조, 좌측 여정형 내비게이션, 단순/전문가 모드, SQL 투명성 원칙을 기준으로 삼았다.
- `style.md`: Oracle Redwood 톤의 warm neutral 배경, 절제된 Redwood Red, 잉크색 primary button, 낮은 시각 소음을 반영했다.
- `docs/research/selectai-reference.md`: 액션 목록, `DBMS_CLOUD_AI.GENERATE`, 프로파일 속성 21개, ACL 분기, conversations, comment 증강 근거를 기술 사실의 기준으로 삼았다.
- `docs/architecture.md`, `docs/api-spec.md`, `docs/security.md`: stateless 호출, 속성 뷰 조회, API envelope, 오류/마스킹, 읽기 전용 게이트를 화면에 반영했다.
- `docs/demo-scenarios.md`: 20분 표준 데모와 5분 영업 데모 흐름을 사이드바와 추천 질문, 대시보드에 반영했다.
- `oracle-database-select-ai-users-guide.pdf`: PDF 메타 확인 완료. 259페이지, Select AI User's Guide, 2026-03-26 생성 문서다. 기술 세부는 추출 정리본인 `docs/research/selectai-reference.md`를 우선 근거로 사용했다.

## 6인 협의체 핵심 결정

- DB 전문가 1: OCI GenAI 기본값에서는 ACL을 "필요 없음"으로 보이고, Resource Principal과 Data Access 상태를 권한 점검의 주 신호등으로 둔다.
- DB 전문가 2: comment 증강은 모호 컬럼 `TABLE1/2/3`의 좌우 비교로 보여주며, c7의 의미가 SQL 정확도를 바꾸는 장면을 클라이맥스로 둔다.
- UX 전문가 1: 비기술 사용자는 사이드바 순서대로만 따라가게 하고, Presales와 파트너는 모든 SQL 미리보기를 펼칠 수 있게 한다.
- UX 전문가 2: Redwood 스타일은 따뜻한 배경과 다크 SQL 패널 대비로 구현하고, 카드 장식보다 업무형 정보 밀도를 우선한다.
- 개발 전문가 1: App Shell, Status Badge, SQL Preview, Result Grid, Error Panel을 재사용 가능한 React 컴포넌트 후보로 보이게 구성한다.
- 개발 전문가 2: 모든 실행성 화면은 `DBMS_CLOUD_AI.GENERATE` 호출 패턴과 마스킹된 SQL을 노출하며, 프로파일 속성은 `USER/DBA_CLOUD_AI_PROFILE_ATTRIBUTES` 뷰 기반으로 표현한다.

## 생성 PNG

- `png/PG-00-onboarding.png`
- `png/PG-01-connections.png`
- `png/PG-02-permissions.png`
- `png/PG-03-profiles.png`
- `png/PG-03a-profile-editor.png`
- `png/PG-03b-profile-detail.png`
- `png/PG-04-playground.png`
- `png/PG-05-chat.png`
- `png/PG-05a-chat-history.png`
- `png/PG-06-enrichment.png`
- `png/PG-07-dashboard.png`
- `png/PG-08-settings.png`
- `png/INDEX-contact-sheet.png`

## 검증 결과

- 데스크톱 PNG 12개 모두 1440x1000으로 생성했다.
- contact sheet PNG를 생성했다.
- PG-03a, PG-04, PG-06, PG-08은 390px 모바일 폭에서 가로 넘침 없이 통과했다.
- 존재하지 않는 액션명과 세션 상태 호출명은 프로토타입 화면에 포함하지 않았다.
- 비밀값은 `***MASKED***` 형태로 표시했다.
- SQL 미리보기와 실행 SQL 패널을 권한, 프로파일, 플레이그라운드, 챗봇, 증강, 설정 화면에 배치했다.
