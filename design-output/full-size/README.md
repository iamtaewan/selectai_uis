# Full Size UI Image Output

## 기준

- 업데이트된 `PRD.md`, `design.md`, `style.md`, `docs/review-findings.md`와 기존 기술 문서를 재검토했다.
- 새로 반영한 주요 변경:
  - 하단 `SQL LOG` 도킹 패널을 full-size 화면에 반영했다.
  - Resource Principal 정책 안내를 `allow dynamic-group <dynamic-group-name> ...` 형식으로 보정했다.
  - `feedback`은 액션 탭이 아니라 P1 권한/상태 항목으로만 표현했다.
  - 실행 화면은 `DBMS_CLOUD_AI.GENERATE(...)` 중심으로 유지했다.

## 산출물

- 위치: `design-output/full-size/png/`
- 페이지별 full-size PNG: 12개
- 전체 contact sheet: `INDEX-contact-sheet-full.png`
- 이미지 크기: 각 페이지 `1440 x 1400`

## 검증

- 주요 페이지 `PG-03a`, `PG-04`, `PG-06`, `PG-08`은 390px 모바일 폭에서 가로 넘침 없이 통과했다.
- 세션 의존 호출명과 존재하지 않는 액션명은 프로토타입 실행 UI에 없다.
- 비밀값은 `***MASKED***` 또는 `********` 방식으로만 표현했다.
