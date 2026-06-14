# Select AI Studio

**Oracle Autonomous Database(ADB)의 Select AI 기능을 클릭만으로 확인·체험하는 스튜디오입니다.**
자연어로 데이터를 묻고(NL2SQL), 생성된 SQL을 검토하고, 메타데이터·피드백으로 정확도를 끌어올리는 Select AI의 전체 흐름을 한 화면에서 손쉽게 둘러볼 수 있습니다. 별도 SQL 작성이나 PL/SQL 호출 없이, 준비 → 체험 순서로 따라가기만 하면 됩니다.

> 대상 DB: **OCI Autonomous Database 26ai** · 접속 사용자: `ADMIN` · 기본 AI Provider: **OCI Generative AI**

---

## 무엇을 할 수 있나요

- **자연어로 질의** — "국가별 고객 수를 알려줘"처럼 한국어로 물으면 Select AI가 SQL을 생성하고 바로 실행해 결과 표로 보여줍니다.
- **SQL을 투명하게 확인** — 생성된 SQL(showsql), 실행 결과(runsql), 설명(explainsql), 자연어 서술(narrate)을 한 번에 비교합니다.
- **정확도 개선 체험** — 테이블/컬럼에 COMMENT·ANNOTATION을 더하거나(메타 강화), 잘못된 결과를 교정 피드백으로 학습시켜(피드백) 같은 질문의 결과가 어떻게 좋아지는지 전/후로 비교합니다.
- **멀티턴 챗봇** — 이전 질문의 맥락을 기억하는 대화형 데이터 질의를 시연합니다.
- **데모 환경 준비 자동화** — 커넥션 연결, 사전 권한 점검·부여, 데모용 SH 스키마 복제까지 화면에서 처리합니다.

모든 LLM 호출은 **DB 내부**(`DBMS_CLOUD_AI.GENERATE`)에서 일어나며, 화면 하단 SQL 로그에 실행된 SQL이 그대로 보여 "지금 이 클릭이 무엇을 실행했는지" 항상 확인할 수 있습니다.

---

## 3분 빠른 시작

```bash
# 1) 백엔드 의존성 (Python 3.12 + uv)
cd backend && uv sync && cd ..

# 2) 프론트엔드 의존성 (Node 22+)
cd frontend && npm install && cd ..

# 3) 동시 기동 (백엔드 :8000 + 프론트 :5173)
bash scripts/run.sh
```

→ 브라우저에서 **http://localhost:5173** 을 엽니다. (`Ctrl+C` 로 동시 종료)

개별 실행이 필요하면:

```bash
cd backend  && uv run uvicorn app.main:app --reload --port 8000   # API 문서: http://localhost:8000/docs
cd frontend && npm run dev                                        # http://localhost:5173
```

---

## 처음 사용 흐름

좌측 메뉴는 **데모 여정 순서**대로 배치되어 있습니다. 위에서 아래로 따라가면 됩니다. (커넥션을 연결하기 전에는 이후 단계가 잠금 상태로 표시됩니다.)

### 준비하기

| 단계 | 메뉴 | 하는 일 |
|---|---|---|
| ① | **커넥션** | wallet zip 업로드 또는 OCI CLI 자동 다운로드로 ADB에 접속해 저장합니다. 연결되면 이후 메뉴가 열립니다. |
| ② | **권한 점검** | Select AI 사전 요구(EXECUTE 권한, Resource Principal/credential, Data Access 등)를 신호등으로 점검하고 부족한 항목을 원클릭으로 적용합니다. |
| ③ | **스키마 복제** | 데모용 **SH 스키마**(판매 이력)를 현재 접속 사용자 스키마로 복제합니다(테이블·데이터·키/FK 제약). 진행 과정이 단계 로그로 표시되며, SH 읽기 권한이 없으면 사유를 안내하고 복제를 막습니다. |
| ④ | **프로파일** | NL2SQL에 쓰일 AI 프로파일을 만듭니다. LLM 모델·대상 테이블(`object_list`)·증강 옵션을 폼으로 설정하고 `CREATE_PROFILE` 실행 전 미리보기를 확인합니다. |
| ⑤ | **메타 강화** | 테이블/컬럼에 한국어 COMMENT·ANNOTATION을 부여해 NL2SQL 정확도를 높입니다. LLM(grok)이 샘플 데이터·관계를 분석해 제안하면 검토 후 일괄 적용할 수 있습니다. |

### 시연하기

| 단계 | 메뉴 | 하는 일 |
|---|---|---|
| ⑥ | **플레이그라운드** | 같은 질문을 runsql·showsql·explainsql·narrate·showprompt로 동시에 실행해 탭으로 비교합니다. |
| ⑦ | **피드백** | 생성 SQL에 긍정/부정(교정 SQL) 피드백을 주고, 저장된 피드백을 직접 확인한 뒤 같은 질문을 재실행해 전/후 결과를 비교합니다. |
| ⑧ | **챗봇** | 이전 턴의 맥락을 유지하는 멀티턴 대화로 데이터를 질의합니다. |

### 기타

- **대시보드** — 환경 건강 신호(권한·프로파일·Data Access 등)를 한눈에 점검합니다.
- **설정** — 기본 프로파일, 표시 모드, 그리고 시연 후 **데모 환경 정리**(앱이 만든 리소스 일괄 제거)를 제공합니다.

> 💡 화면 하단의 **SQL 로그 터미널**(`Ctrl/Cmd + \``)에는 DB에서 실행된 모든 SQL이 시계열로 쌓입니다. GENERATE 호출과 실행 쿼리를 복수 라인으로 보기 좋게 표시해, 내부 동작을 그대로 학습·시연할 수 있습니다.

---

## 사전 요구

| 도구 | 버전 | 비고 |
|---|---|---|
| Python | 3.12 | 백엔드 (`uv`로 관리) |
| uv | 최신 | `pip install uv` 또는 공식 설치 스크립트 |
| Node.js | 22+ | 프론트엔드 (Vite) |
| OCI CLI | 선택 | wallet **자동 다운로드** 기능 사용 시. 미설치 시 wallet zip 수동 업로드로 폴백 |
| `~/.oci/config` | 선택 | OCI CLI 인증용. 앱은 이 파일을 읽거나 수정하지 않습니다 |

이용하려면 접속 가능한 **ADB 26ai 인스턴스**, **mTLS wallet**(또는 OCI CLI 다운로드 권한), `ADMIN` 비밀번호가 필요합니다.

---

## 데이터 저장 · 보안

- 앱 상태는 `~/.selectai/`의 JSON 파일(`connections.json`·`settings.json`·`resources.json`)과 wallet 보관소에만 저장됩니다(SQLite 미사용).
- `ADMIN` 비밀번호·wallet은 `~/.selectai/`(권한 0700)에 **Fernet 암호화**로 저장하고, 로그·응답·SQL 표시에서 마스킹합니다.
- LLM이 생성한 SQL 중 **비 SELECT(INSERT/UPDATE/DELETE/DDL)는 앱 계층에서 자동 차단**됩니다.
- 백엔드는 stateless 단일 패턴(`GENERATE(... params => :params_json)`, 바인드 변수)으로만 Select AI를 호출합니다.
- 시연 후에는 **설정 → 데모 환경 정리**로 앱이 생성한 프로파일·credential·대화·데모 테이블을 일괄 제거하세요.

---

## 자주 묻는 문제

- **챗봇/질의 응답이 느려요(10~20초).** 프로파일의 LLM 모델이 무거운 추론형(예: `xai.grok-4`)일 수 있습니다. **프로파일 편집**에서 빠른 모델(`xai.grok-4.3`, `xai.grok-4-fast-non-reasoning`)로 바꾸면 크게 빨라집니다. 또한 `narrate`는 LLM을 2번 호출하므로, 자연어 서술이 필요 없으면 `runsql`/`showsql`이 더 빠릅니다.
- **"Data access is disabled" 오류.** `narrate`·합성 데이터 등 **실데이터를 LLM에 보내는 동작**에만 Data Access가 필요합니다. 권한 점검 화면에서 활성화하세요(앱이 대체로 자동 복구). SQL 생성·피드백·메타·복제만 본다면 필요 없습니다.
- **메타/복제에서 권한 오류.** 접속 사용자가 소유하지 않은 스키마(예: SH 원본)는 COMMENT/ALTER가 제한됩니다. 본인 스키마(복제본) 대상으로 수행하거나 권한을 확보하세요.
- **피드백을 줬는데 쿼리가 안 바뀌어요.** 긍정 피드백은 "현재 SQL이 정답"으로 강화하는 것이라 그대로가 정상입니다. 쿼리를 바꾸려면 **부정 + 교정 SQL**로 제출하세요.

---

## 컨테이너 배포 (단일 컨테이너)

프론트(정적 빌드)와 백엔드를 **하나의 이미지**로 묶어 포트 하나(8000)로 서빙합니다. FastAPI가 빌드된 SPA를 직접 서빙하므로 nginx·CORS·별도 프록시가 필요 없습니다. (python-oracledb thin 모드라 Oracle Instant Client도 불필요)

```bash
# 빌드 + 실행 (compose)
docker compose up -d --build      # → http://localhost:8000

# 또는 docker 직접
docker build -t selectai-studio .
docker run -d -p 8000:8000 -v selectai-data:/data selectai-studio
```

- **영속 볼륨 필수** — 커넥션·wallet·`secret.key`가 `/data`(`APP_DATA_DIR`)에 저장됩니다. 볼륨이 없으면 재시작 시 모두 사라집니다.
- **암호화 키** — `APP_SECRET_KEY` 미설정 시 `/data/secret.key`가 자동 생성되어 볼륨에 유지됩니다. 여러 환경에서 같은 데이터를 쓰려면 `APP_SECRET_KEY`를 고정하세요.
- **wallet 획득** — 기본은 화면에서 **wallet zip 수동 업로드**를 권장합니다(이미지에 OCI CLI 미포함). 자동 다운로드가 필요하면 OCI CLI를 이미지에 추가하고 `~/.oci`를 마운트하세요(`docker-compose.yml` 주석 참고).

## 테스트

```bash
cd backend  && uv run pytest -q                  # 백엔드 단위 테스트 (oracledb 모킹, 실 DB 불필요)
cd frontend && npx tsc --noEmit && npm run build # 프론트 타입 검사 + 빌드
```

---

## 문서 맵

설계·API·보안·데모 시나리오 등 상세 문서는 [`docs/INDEX.md`](docs/INDEX.md)에서 시작하세요. 기능 근거가 된 원문 가이드는 [`docs/research/`](docs/research/)에 있습니다.
