# Style Guide — Select AI Demo Studio (Oracle Redwood 룩앤필)

| 항목 | 내용 |
|---|---|
| 문서명 | style.md — Redwood 스타일 가이드 |
| 버전 | v1.0 (2026-06-12) |
| 작성자 | 비주얼 디자이너 (전문가 5/8) |
| 관련 문서 | `PRD.md` (기능 요구사항), `docs/architecture.md` (기술 설계), `docs/research/selectai-reference.md` (도메인 근거) |
| 목표 | **Oracle JET(공식 Redwood 컴포넌트) 없이**, React + CSS 변수 토큰만으로 Redwood 룩앤필을 재현 |

---

## 1. Redwood 디자인 철학과 이 데모에서의 적용 원칙

### 1.1 Redwood 철학 요약

Oracle Redwood는 Oracle의 전사 디자인 시스템으로, 다음 특징을 가진다.

1. **따뜻한 뉴트럴(warm neutral)**: 차가운 블루-그레이가 아닌, 베이지·웜그레이 계열 배경(`#FBF9F8` 류) 위에 잉크에 가까운 짙은 텍스트(`#161513` 류)를 얹는다. "종이 위의 잉크" 감각.
2. **절제된 시그니처 레드**: Redwood Red(`#C74634`)는 브랜드 식별용 포인트로만 쓰고, 화면을 붉게 물들이지 않는다. 주요 액션 버튼은 오히려 짙은 잉크색/뉴트럴 다크가 기본이다.
3. **낮은 시각적 소음**: 얇은 보더, 은은한 그림자, 충분한 화이트스페이스. 데이터(표, SQL, 결과)가 주인공이고 크롬(chrome)은 조연.
4. **명료한 위계와 가이드형 UX**: 큰 페이지 타이틀 → 섹션 헤더 → 본문의 뚜렷한 타이포 위계, 단계형(Stepper/Train) 진행 표시.
5. **상태의 즉각적 전달**: 성공/경고/오류/정보 상태 컬러와 배지를 일관되게 사용해 "지금 환경이 데모 가능한가"를 즉시 읽게 한다.

### 1.2 이 데모에서의 적용 원칙

PRD의 페르소나(P1 Presales / P2 영업 / P3 파트너)와 기능(FR-01~09)에 맞춰 다음을 디자인 원칙으로 삼는다.

| # | 원칙 | 근거 (PRD) |
|---|---|---|
| A1 | **"데모 가능 상태"가 항상 보이게**: 신호등(상태 배지)·점검 체크리스트를 전 화면 공통 패턴으로 | FR-03, FR-09, G5 |
| A2 | **SQL은 1급 시민**: 모든 실행 화면에 GENERATE SQL 펼침 영역 — 코드 블록 스타일을 본문과 명확히 구분되는 다크 패널로 통일 | FR-06 수용 기준, design.md 설계 전제 5 |
| A3 | **비교가 핵심 레이아웃**: 좌우 분할 비교(comments off/on, 대화 유무)를 위한 2컬럼 패널 패턴을 토큰화 | FR-07, FR-08 |
| A4 | **학습 해설은 보조 톤**: 한국어 해설(21개 속성 설명, 근거 페이지)은 본문보다 한 단계 연한 텍스트 + 인포 패널로, 데이터를 가리지 않게 | FR-04, P3 페르소나 |
| A5 | **비개발자 안전망**: 파괴적 액션(삭제, DDL 적용)은 danger 스타일 + 확인 단계, 추천 프롬프트는 큼직한 클릭 타깃 | P2 페르소나, G1 |
| A6 | **Redwood Red는 브랜딩과 위험 강조에만**: 앱 헤더 액센트, 로고, danger 계열에 한정. primary 버튼은 잉크색 | Redwood 철학 2 |

---

## 2. 컬러 팔레트 — CSS 변수 토큰

Redwood 시그니처 컬러를 기준으로 한 토큰 정의. **이 파일이 곧 `src/styles/tokens.css`의 원본 명세**다.

```css
:root {
  /* ===== 브랜드 ===== */
  --color-brand:            #C74634;  /* Redwood Red — 헤더 액센트, 로고, 포커스 포인트 */
  --color-brand-dark:       #A33A2B;  /* 브랜드 hover/액티브 */
  --color-brand-tint:       #FBEDEA;  /* 브랜드 연한 배경 (배너, 선택 강조) */

  /* ===== 뉴트럴 (웜 그레이 스케일 — Redwood의 핵심 질감) ===== */
  --color-neutral-0:        #FFFFFF;
  --color-neutral-10:       #FBF9F8;  /* 앱 기본 배경 (warm paper) */
  --color-neutral-20:       #F5F4F2;  /* 패널/사이드바 배경 */
  --color-neutral-30:       #E4E1DD;  /* 보더 기본 */
  --color-neutral-40:       #D4D0CB;  /* 보더 강조, 비활성 컨트롤 */
  --color-neutral-50:       #ABA7A2;  /* 비활성 텍스트, 플레이스홀더 */
  --color-neutral-60:       #7A756F;  /* 보조 텍스트 (해설, 캡션) */
  --color-neutral-70:       #4F4A45;  /* 서브 헤딩 */
  --color-neutral-80:       #312D2A;  /* 다크 패널 배경 (코드 블록, 앱 헤더) */
  --color-neutral-90:       #161513;  /* 본문 텍스트 (잉크) */

  /* ===== 상태 컬러 ===== */
  --color-success:          #2E7D32;  /* 통과/연결 성공 */
  --color-success-tint:     #E8F3E8;
  --color-warning:          #B7790A;  /* 주의 (예: deprecated 모델, P1 미점검) */
  --color-warning-tint:     #FCF0DC;
  --color-danger:           #C7402E;  /* 오류/삭제 (브랜드 레드와 동족 톤) */
  --color-danger-tint:      #FBEDEA;
  --color-info:             #1F6FB5;  /* 정보/해설/근거 페이지 */
  --color-info-tint:        #E6F0F8;
  --color-running:          #6B4FA0;  /* 실행 중 (LLM 호출 대기) */
  --color-running-tint:     #EFEAF7;

  /* ===== 인터랙션 ===== */
  --color-action-primary:        var(--color-neutral-90); /* primary 버튼 배경 = 잉크 */
  --color-action-primary-hover:  #2C2A27;
  --color-focus-ring:            #1F6FB5;                 /* 포커스 아웃라인 (접근성) */
  --color-link:                  #1F6FB5;
  --color-overlay:               rgba(22, 21, 19, 0.4);   /* 모달 딤 */

  /* ===== 코드/SQL 블록 (다크 패널 — 라이트 UI 속 유일한 다크 영역) ===== */
  --color-code-bg:          #25221F;
  --color-code-text:        #F5F4F2;
  --color-code-keyword:     #F0A878;  /* SQL 키워드 (SELECT, BEGIN …) */
  --color-code-string:      #A8C9A0;  /* 문자열 리터럴 */
  --color-code-comment:     #8A857F;
  --color-code-accent:      #E89A8C;  /* 함수명 (DBMS_CLOUD_AI.GENERATE) */
}
```

**사용 규칙**

- 본문 텍스트 `--color-neutral-90` / 보조·해설 `--color-neutral-60` 아래로 내려가지 않는다 (대비 4.5:1 유지).
- Redwood Red(`--color-brand`)는 ① 상단 앱 헤더의 좌측 액센트 바 또는 로고, ② 활성 탭 인디케이터, ③ danger 계열 외에는 쓰지 않는다.
- 상태 컬러는 반드시 `*-tint` 배경 + 본색 텍스트/아이콘 조합으로 배지·배너를 구성한다 (단색 채움 지양).

---

## 3. 타이포그래피

### 3.1 폰트 전략 — Oracle Sans 대체

Oracle Sans는 라이선스상 재배포 불가이므로 **무료 웹폰트 폴백 스택**을 쓴다. Oracle Sans와 골격이 유사한 휴머니스트 산세리프를 1순위로 한다. 한국어 UI이므로 한글 폰트를 반드시 스택에 포함한다.

```css
:root {
  /* 본문/UI: Oracle Sans 대체 */
  --font-sans: "Inter", "Pretendard", "Noto Sans KR",
               -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;

  /* 코드/SQL: Oracle Sans Mono 대체 */
  --font-mono: "JetBrains Mono", "SF Mono", "D2Coding",
               Consolas, "Courier New", monospace;
}
```

- 권장 로딩: `Inter`(영문/숫자) + `Pretendard`(한글)를 self-host(woff2). CDN 의존을 피해 OCI Compute 오프라인 데모에서도 동일하게 렌더링.
- 숫자는 표/지표에서 `font-variant-numeric: tabular-nums` 적용 (SQL 결과 그리드 정렬감).

### 3.2 크기/굵기 스케일 토큰

```css
:root {
  --text-xs:    0.75rem;   /* 12px — 배지, 근거 페이지 표기(p84 등), 캡션 */
  --text-sm:    0.8125rem; /* 13px — 보조 해설, 테이블 셀 보조 */
  --text-base:  0.875rem;  /* 14px — 본문, 폼, 테이블 기본 (데이터 밀도 우선) */
  --text-md:    1rem;      /* 16px — 챗 버블, 강조 본문 */
  --text-lg:    1.125rem;  /* 18px — 카드/패널 제목 */
  --text-xl:    1.375rem;  /* 22px — 섹션 헤더 */
  --text-2xl:   1.75rem;   /* 28px — 페이지 타이틀 */

  --weight-regular:  400;
  --weight-medium:   500;  /* 라벨, 탭, 테이블 헤더 */
  --weight-semibold: 600;  /* 패널 제목, 버튼 */
  --weight-bold:     700;  /* 페이지 타이틀, 핵심 수치 */

  --leading-tight:  1.3;   /* 헤딩 */
  --leading-normal: 1.55;  /* 본문/해설 */
  --leading-code:   1.6;   /* 코드 블록 */
}
```

위계 매핑: 페이지 타이틀(`--text-2xl`/bold) → 섹션(`--text-xl`/semibold) → 패널 제목(`--text-lg`/semibold) → 본문(`--text-base`) → 해설/캡션(`--text-sm`·`--text-xs`, `--color-neutral-60`).

---

## 4. 레이아웃 / 스페이싱

### 4.1 앱 셸 (App Shell)

```
┌──────────────────────────────────────────────┐
│ 헤더 56px — 좌: 브랜드 액센트+제품명, 우: 활성 커넥션·기본 프로파일 배지 │
├──────────┬───────────────────────────────────┤
│ 사이드 네비 │  콘텐츠 영역 (max-width 1280px, 중앙 정렬)            │
│ 240px    │  여정 순서대로: 연결 → 권한 → 프로파일 → 액션 → 챗봇 → 증강비교 → 대시보드 │
└──────────┴───────────────────────────────────┘
```

- 사이드 네비는 PRD §5 사용자 여정 순서를 그대로 메뉴 순서로 사용 (가이드형 UX).
- 비교 화면(FR-07/08)은 콘텐츠 영역을 `1fr 1fr` 2컬럼 그리드로 분할, 컬럼 간격 `--space-6`.

### 4.2 스페이싱·라운딩·그림자 토큰

```css
:root {
  /* 4px 베이스 스페이싱 스케일 */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  /* 라운딩 — Redwood는 과한 라운딩을 쓰지 않음 */
  --radius-sm:   4px;   /* 입력 필드, 배지, 코드 인라인 */
  --radius-md:   6px;   /* 버튼, 탭 */
  --radius-lg:   8px;   /* 카드, 패널, 모달 */
  --radius-full: 999px; /* 칩(추천 프롬프트), 아바타, 신호등 점 */

  /* 그림자 — 은은하게, 웜 잉크 기반 */
  --shadow-sm: 0 1px 2px rgba(22, 21, 19, 0.06);
  --shadow-md: 0 2px 8px rgba(22, 21, 19, 0.10);   /* 카드 hover, 드롭다운 */
  --shadow-lg: 0 8px 24px rgba(22, 21, 19, 0.16);  /* 모달, 토스트 */

  /* 보더 */
  --border-default: 1px solid var(--color-neutral-30);
  --border-strong:  1px solid var(--color-neutral-40);
}
```

### 4.3 카드/패널 기본 스타일

```css
.panel {
  background: var(--color-neutral-0);
  border: var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
}
.panel--explain { /* 한국어 해설/학습 패널 (FR-04) */
  background: var(--color-info-tint);
  border-color: transparent;
  color: var(--color-neutral-70);
  font-size: var(--text-sm);
}
```

- 앱 배경 `--color-neutral-10` 위에 흰 패널을 얹는 구성이 기본.
- 전/후 비교 패널(FR-08): "전(comments off)" 패널 상단 보더 `--color-warning`, "후(comments on)" 패널 상단 보더 `--color-success` 3px 액센트로 직관 구분.

---

## 5. 핵심 컴포넌트 스타일 명세

### 5.1 버튼

| 변형 | 배경 | 텍스트 | 보더 | 용도 |
|---|---|---|---|---|
| **primary** | `--color-action-primary` (잉크) | `--color-neutral-0` | 없음 | 실행, 연결, 생성, 원클릭 적용 |
| **secondary** | `--color-neutral-0` | `--color-neutral-90` | `--border-strong` | 테스트, 미리보기, 취소 |
| **danger** | `--color-danger` | `--color-neutral-0` | 없음 | 삭제(커넥션/프로파일/대화), DROP 계열 |
| **ghost** | 투명 | `--color-link` | 없음 | "SQL 펼쳐 보기", 보조 링크 액션 |

공통: 높이 36px(기본)/44px(P2용 추천 프롬프트 등 큰 타깃), `--radius-md`, `--weight-semibold`, `--text-base`. hover 시 배경 1단계 어둡게, `:focus-visible`에 `outline: 2px solid var(--color-focus-ring); outline-offset: 2px`. 로딩 중에는 스피너 + 비활성(중복 호출 방지 — LLM 호출은 느릴 수 있음).

danger 버튼은 항상 확인 다이얼로그를 동반한다 (원칙 A5).

### 5.2 입력 필드 (텍스트/셀렉트/파일 업로드)

```css
.input {
  height: 36px;
  padding: 0 var(--space-3);
  background: var(--color-neutral-0);
  border: var(--border-strong);
  border-radius: var(--radius-sm);
  font: var(--weight-regular) var(--text-base) var(--font-sans);
}
.input:focus { border-color: var(--color-focus-ring); box-shadow: 0 0 0 1px var(--color-focus-ring); }
.input--error { border-color: var(--color-danger); }
.input--error + .field-message { color: var(--color-danger); font-size: var(--text-sm); }
```

- 라벨은 필드 위(`--text-sm`/medium), 해설은 필드 아래(`--text-xs`, `--color-neutral-60`) — 21개 프로파일 속성 폼(FR-04)에서 라벨+한국어 해설+근거 페이지(예: "p84") 3단 구성.
- wallet zip 업로드(FR-01): 점선 보더(`2px dashed --color-neutral-40`) 드롭존, 업로드 후 추출된 TNS alias를 라디오 카드 목록으로 표시.
- 비밀번호 필드는 마스킹 + 표시 토글, 값은 어떤 UI 텍스트에도 에코하지 않음 (FR-01 수용 기준).

### 5.3 탭 (액션 전환 — FR-06의 runsql/showsql/explainsql/narrate/chat)

- 언더라인 탭: 비활성 텍스트 `--color-neutral-60`, 활성 텍스트 `--color-neutral-90` + 하단 3px 인디케이터 `--color-brand` (Redwood Red 허용처 ②).
- 탭 라벨은 액션 키워드 원문(`runsql` 등, `--font-mono`) + 한국어 부제("SQL 실행") 2줄 구성 — 학습 효과(A4).
- P1 액션 중 `showprompt`는 탭에 `P1` 배지를 달아 비활성 노출 가능하다. `feedback`은 액션 탭이 아니라 결과 카드의 👍/👎 피드백 버튼으로 통합한다.

### 5.4 테이블 (SQL 결과 그리드)

```css
.grid          { width: 100%; border: var(--border-default); border-radius: var(--radius-lg); overflow: hidden; }
.grid th       { background: var(--color-neutral-20); font-weight: var(--weight-medium);
                 font-size: var(--text-sm); color: var(--color-neutral-70);
                 text-align: left; padding: var(--space-2) var(--space-3);
                 border-bottom: var(--border-strong); position: sticky; top: 0; }
.grid td       { padding: var(--space-2) var(--space-3); font-size: var(--text-base);
                 border-bottom: var(--border-default); }
.grid td.num   { text-align: right; font-variant-numeric: tabular-nums; }
.grid tr:hover { background: var(--color-neutral-10); }
```

- 행 높이 36px, 1000행 이상은 가상 스크롤 또는 페이지네이션. NULL은 `--color-neutral-50` 이탤릭 `(null)`.
- 그리드 상단 메타바: 행 수 · 응답 시간(latency, FR-06 수용 기준) · CSV 다운로드 ghost 버튼.

### 5.5 챗 버블 (FR-07)

| 요소 | 스타일 |
|---|---|
| 사용자 버블 | 우측 정렬, 배경 `--color-neutral-80`, 텍스트 `--color-neutral-10`, `--radius-lg`(우하단 `--radius-sm`) |
| AI 버블 | 좌측 정렬, 배경 `--color-neutral-0`, `--border-default`, 텍스트 `--color-neutral-90` |
| 턴 메타 | 버블 하단 `--text-xs`: 사용 액션 배지(`narrate` 등) + latency + "SQL 보기" ghost 링크 |
| 결과 내장 | AI 버블 안에 §5.4 그리드 또는 §5.6 SQL 블록을 인라인 삽입 가능 |
| 추천 프롬프트 칩 | `--radius-full`, `--color-neutral-20` 배경, 44px 높이 (P2 큰 타깃) |
| 비교 모드 | 좌(대화 없음)/우(conversation_id 있음) 2컬럼, 각 컬럼 헤더에 info 배지로 설명 |

입력창은 하단 고정, 전송 버튼은 primary. 응답 대기 중에는 AI 버블 위치에 `--color-running` 점 3개 펄스 애니메이션.

### 5.6 코드/SQL 블록 (모든 실행 화면 공통 — design.md 설계 전제 5)

```css
.code-block {
  background: var(--color-code-bg);
  color: var(--color-code-text);
  font: var(--text-sm)/var(--leading-code) var(--font-mono);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  overflow-x: auto;
}
.code-block__toolbar { /* 우상단: 복사 버튼, 라벨("실행된 GENERATE SQL") */ }
```

- 기본은 `<details>` 펼침(접힌 상태) — 라벨: "이 버튼이 실제로 실행한 SQL 보기" (P3 페르소나 문구).
- 구문 강조는 §2의 `--color-code-*` 토큰 사용. 강조 대상: SQL 키워드, `DBMS_CLOUD_AI.*` 함수명, 문자열(프롬프트/JSON).
- CREATE_PROFILE / GRANT / COMMENT DDL "미리보기"(FR-03/04/05/08)도 동일 컴포넌트 재사용 — 단, 미리보기에는 상단에 `미리보기 — 아직 실행되지 않음` warning 배지를 부착.

### 5.7 상태 배지 (성공/오류/실행중/대기)

```css
.badge { display: inline-flex; align-items: center; gap: var(--space-1);
         height: 22px; padding: 0 var(--space-2);
         border-radius: var(--radius-full);
         font-size: var(--text-xs); font-weight: var(--weight-medium); }
.badge--success { background: var(--color-success-tint); color: var(--color-success); }
.badge--error   { background: var(--color-danger-tint);  color: var(--color-danger); }
.badge--warning { background: var(--color-warning-tint); color: var(--color-warning); }
.badge--running { background: var(--color-running-tint); color: var(--color-running); } /* 점 펄스 */
.badge--info    { background: var(--color-info-tint);    color: var(--color-info); }
.badge--neutral { background: var(--color-neutral-20);   color: var(--color-neutral-60); } /* 해당없음 */
```

- 권한 점검(FR-03) 체크리스트: 항목별 `통과(success) / 실패(error) / 해당없음(neutral — 예: OCI GenAI일 때 ACL)` 배지 + 근거 SQL 펼침.
- 대시보드(FR-09) 신호등: `--radius-full` 12px 점 3색(success/warning/danger) + 라벨.
- ORA 오류 표시: error 배지 + 오류 원문(`--font-mono`) + 한국어 해설 + "재시도"/"복구" 버튼을 한 배너(`--color-danger-tint` 배경)에 묶음 (G5, R1·R2).

### 5.8 토스트

- 위치: 우상단, `--shadow-lg`, `--radius-lg`, 폭 360px, 자동 닫힘 5초(success/info) — 오류 토스트는 수동 닫기.
- 구조: 좌측 상태 컬러 4px 액센트 바 + 아이콘 + 제목(`--weight-semibold`) + 본문 1~2줄 + (선택) 액션 링크("점검 다시 실행").
- 장시간 작업(권한 적용, 모호 스키마 생성)은 running 토스트 → 완료 시 success로 치환.

### 5.9 SQL 로그 터미널 (SqlLogTerminal — design.md §1.3)

VS Code 통합 터미널을 본뜬 하단 도킹 패널(DB Interaction 화면 PG-01~07 공통). 라이트 UI 속 다크 영역은 코드/SQL 블록(§5.6)과 이 패널 둘뿐이며, **§2의 `--color-code-*` 토큰을 그대로 재사용한다 — 새 색상 토큰을 추가하지 않는다** (A2 "SQL은 1급 시민"의 연장).

| 요소 | 스타일 |
|---|---|
| 패널 높이 | 기본 240px / 최소 120px / 최대 = 콘텐츠 영역 전체(최대화 상태). 상단 6px 드래그 핸들, hover·드래그 중 `--color-focus-ring` 표시 |
| 패널 본문 | 배경 `--color-code-bg`(#25221F), 텍스트 `--color-code-text`, `--font-mono`, `--text-sm`/`--leading-code`. 도킹 패널이므로 라운딩 없음(카드 아님), 상단 보더 `--border-strong` |
| 헤더 바 | 높이 32px, 배경 `--color-neutral-80`, 좌: 타이틀 `SQL LOG`(`--text-xs`/`--weight-semibold`, letter-spacing 0.08em) + 카운트 배지, 우: 아이콘 버튼 4개 — 지우기·복사·최대화/복원·닫기(Lucide 16px, `currentColor`, `:focus-visible` 링 §5.1 공통) |
| 카운트 배지 | §5.7 배지 문법의 다크 변형: 배경 `rgba(255,255,255,0.12)`, 텍스트 `--color-code-text`, `--radius-full` |
| 로그 라인 | 타임스탬프 `[HH:MM:SS]` = `--color-code-comment`, 페이지/기능 태그 = `--color-code-accent`, SQL 본문 = §5.6과 동일 구문 강조 토큰(`--color-code-keyword`/`-string`/`-accent`), latency `— 123ms` = `--color-code-comment` |
| 라인 상태 | 성공 = 기본 구문 강조 / 오류 = 라인 좌측 2px `--color-danger` 액센트 + ORA 코드 `--color-danger` 텍스트 / 실행 중 = `--color-running` 스피너(완료 시 결과 상태로 치환) |
| 상태바 토글 | 글로벌 푸터(상태바)의 `▣ SQL LOG (n)` 항목: `--text-xs`, 닫힘 시 `--color-neutral-60`, 열림(활성) 시 `--color-neutral-90` + 상단 2px `--color-brand` 인디케이터 — 활성 탭(§5.3)과 동일 문법(Redwood Red 허용처 ②) |
| 단축키/키보드 | Ctrl/Cmd + ` 토글, 패널 포커스 시 ↑/↓ 라인 탐색, Esc = 닫기 |

**VS Code 유사점과 Redwood 정합성**: VS Code에서 차용하는 것은 ⓐ 하단 도킹 + 드래그 리사이즈, ⓑ 상태바 클릭/단축키 show·no show, ⓒ 모노스페이스 다크 터미널 질감의 3가지 **행동 패턴**에 한정한다. 색은 VS Code의 차가운 다크(#1E1E1E)·블루 액센트(#007ACC)가 아닌 본 가이드의 웜 다크 토큰(`#25221F`, `--color-neutral-80`)을 쓰고, 활성 액센트는 A6 원칙대로 Redwood Red 인디케이터에만 허용한다. §7.3의 "블루 계열 금지"는 이 패널에도 그대로 적용된다.

---

## 6. 다크/라이트 모드 결정

**결정: 라이트 모드 단일 (다크 모드 미지원).** 단, 코드/SQL 블록만 다크 패널로 유지한다.

근거:

1. **데모 환경 특성**: 주 사용 맥락이 고객 미팅룸 빔프로젝터/대형 TV 공유 화면 — 라이트 UI가 투사 환경에서 가독성·대비가 안정적이다.
2. **Redwood 정합성**: Redwood의 기본 표현은 웜 뉴트럴 라이트 테마이며, 본 가이드의 컬러 토큰도 라이트 기준으로 검증됐다.
3. **범위 관리**: PRD 비목표(프로덕션급 완성도 배제)와 일관 — 토큰 이중화·QA 비용을 P0 기능에 투입한다.
4. **대비 효과**: 라이트 UI 속 다크 SQL 블록은 "실행된 SQL"에 시선을 모으는 의도적 장치(A2)로, 모드 토글보다 데모 가치가 크다.

추후 다크 모드가 필요해지면 §2 토큰이 시맨틱 변수로 추상화돼 있으므로 `[data-theme="dark"]` 셀렉터에 값만 재정의하면 된다 (구조 변경 불필요).

---

## 7. 구현 가이드

### 7.1 적용 방법 — CSS 변수 + Tailwind 연동

1. `src/styles/tokens.css`에 §2~4의 `:root` 토큰 블록을 그대로 작성하고 앱 진입점에서 최우선 import.
2. Tailwind 사용 시(권장: Tailwind CSS v4) 토큰을 테마로 매핑해 유틸리티에서 사용:

```css
/* tailwind v4 — CSS-first 설정 */
@theme {
  --color-brand: #C74634;
  --color-ink: #161513;
  --color-paper: #FBF9F8;
  /* ... tokens.css 값을 @theme로 노출 → bg-paper, text-ink, border-neutral-30 등으로 사용 */
}
```

3. 컴포넌트는 §5 명세를 단일 소스로 구현: `Button`, `Field`, `Tabs`, `ResultGrid`, `ChatBubble`, `SqlBlock`, `StatusBadge`, `Toast`, `Panel`, `ComparePanes`, `SqlLogTerminal` 11종을 `src/components/ui/`에 공용화 (`SqlLogTerminal`은 앱 셸 전역 1인스턴스 — design.md §1.3). 페이지(FR별 화면)는 이 11종만 조합한다 — 임의 색상/스페이싱 하드코딩 금지(코드 리뷰 체크 항목).
4. 임의 값 사용을 막기 위해 stylelint에 `declaration-property-value-allowed-list`(color는 `var(--color-*)`만 허용) 류 규칙 추가 권장.

### 7.2 추천 라이브러리

| 용도 | 추천 | 비고 |
|---|---|---|
| 아이콘 | **Lucide React** | 1.5px 스트로크의 중립적 라인 아이콘 — Redwood 아이콘 톤과 유사. 크기 16/20px, `currentColor` |
| SQL 구문 강조 | **Shiki** (또는 highlight.js + sql) | §2 `--color-code-*` 값으로 커스텀 테마 정의 |
| 헤드리스 컴포넌트 | **Radix UI** (Tabs/Dialog/Toast/Tooltip) | 접근성(키보드/ARIA) 확보, 스타일은 본 가이드 토큰으로 |
| 결과 그리드 | **TanStack Table** + 가상 스크롤(`@tanstack/react-virtual`) | 대용량 runsql 결과 대응 |
| 웹폰트 | Inter + Pretendard self-host (woff2) | CDN 미의존 — OCI Compute 배포·오프라인 데모 안전 |
| 차트(P1 대시보드) | 선택 시 Recharts | 색상은 상태 토큰만 사용 |

### 7.3 금지 사항 (Redwood 룩앤필 훼손 방지)

- Oracle JET / Redwood 공식 CSS·폰트(Oracle Sans) 파일 직접 번들 금지 (라이선스).
- 파란 계열 primary 버튼, 차가운 블루-그레이 배경(`#F0F4F8` 류) 사용 금지 — 웜 뉴트럴 유지.
- Redwood Red의 대면적 사용(헤더 전체 채움, primary 버튼) 금지 — §1.2 A6.
- 8px 초과 라운딩, 강한 그림자, 그라데이션 배경 금지.

---

## 부록 — 핵심 토큰 요약표

| 그룹 | 핵심 토큰 | 값 |
|---|---|---|
| 브랜드 | `--color-brand` | `#C74634` (Redwood Red) |
| 텍스트/배경 | `--color-neutral-90` / `--color-neutral-10` | `#161513` / `#FBF9F8` |
| primary 버튼 | `--color-action-primary` | `#161513` (잉크) |
| 상태 | success/warning/danger/info/running | `#2E7D32` / `#B7790A` / `#C7402E` / `#1F6FB5` / `#6B4FA0` |
| 코드 블록 | `--color-code-bg` | `#25221F` (다크 패널) |
| 폰트 | `--font-sans` / `--font-mono` | Inter+Pretendard / JetBrains Mono |
| 본문 크기 | `--text-base` | 14px |
| 스페이싱 | `--space-1`~`--space-8` | 4·8·12·16·24·32·48·64px |
| 라운딩 | `--radius-sm/md/lg` | 4/6/8px |
| 테마 | 라이트 단일 + 다크 SQL 블록 | §6 |
