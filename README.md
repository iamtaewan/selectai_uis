# Select AI Demo Studio

Oracle **Select AI**(NL2SQL)를 고객에게 쉽게 시연하기 위한 데모 웹 애플리케이션입니다. 오라클 Presales·영업·파트너가 클릭 몇 번으로 자연어 질의, 챗봇, 메타데이터(COMMENT) 증강 효과를 보여줄 수 있습니다.

> 대상 DB: **OCI Autonomous Database 26ai** · DB 사용자: `admin` · 기본 AI Provider: **OCI Generative AI**

---

## 아키텍처 한눈에

```
React SPA (Vite, :5173)  ──/api──▶  FastAPI (uvicorn, :8000)  ──mTLS wallet──▶  ADB 26ai
                                          │                                    (DBMS_CLOUD_AI.GENERATE)
                                          └─ ~/.selectai/ (JSON 저장소 + wallet + secret.key)   └──▶ OCI Generative AI
```

- **LLM 호출은 전적으로 DB 내부**에서 일어납니다 (`DBMS_CLOUD_AI.GENERATE`). 백엔드는 OCI SDK가 필요 없고, 예외는 wallet 자동 다운로드 시 OCI CLI subprocess 호출뿐입니다.
- 모든 Select AI 실행은 **단일 패턴**(`GENERATE(... params=>:params_json)`, 바인드 변수)으로 통일됩니다. 세션 상태(`SET_PROFILE`/`SET_CONVERSATION_ID`/`SELECT AI` 키워드)는 stateless 백엔드에서 사용하지 않습니다.
- 앱 영속 상태는 `~/.selectai/`의 JSON 파일 3종(`connections.json`·`settings.json`·`resources.json`)과 wallet 보관소뿐입니다. (SQLite 미사용)
- 상세 설계는 [`docs/INDEX.md`](docs/INDEX.md)에서 시작하세요.

## 사전 요구

| 도구 | 버전 | 비고 |
|---|---|---|
| Python | 3.12 | 백엔드 (`uv`로 관리) |
| uv | 최신 | `pip install uv` 또는 공식 설치 스크립트 |
| Node.js | 22+ | 프론트엔드 (Vite) |
| OCI CLI | 선택 | wallet **자동 다운로드** 기능 사용 시. 미설치 시 wallet zip 수동 업로드로 폴백 |
| `~/.oci/config` | 선택 | OCI CLI 인증 (자동 다운로드 시). 앱은 이 파일을 읽거나 수정하지 않음 |

데모 시연에는 접속 가능한 **ADB 26ai 인스턴스**와 **mTLS wallet**(또는 OCI CLI 다운로드 권한), `admin` 비밀번호가 필요합니다.

## 설치 & 실행

```bash
# 1) 백엔드 의존성
cd backend && uv sync && cd ..

# 2) 프론트엔드 의존성
cd frontend && npm install && cd ..

# 3) 동시 기동 (백엔드 :8000 + 프론트 :5173)
bash scripts/run.sh
# → 브라우저에서 http://localhost:5173
```

개별 실행:

```bash
cd backend  && uv run uvicorn app.main:app --reload --port 8000   # API 문서: http://localhost:8000/docs
cd frontend && npm run dev                                        # http://localhost:5173
```

## 데모 준비 흐름 (사이드바 순서 = 데모 여정)

1. **커넥션** (`/connections`) — wallet zip 업로드 또는 OCI CLI 자동 다운로드 + `admin` 접속·저장
2. **권한 점검** (`/permissions`) — Select AI 사전 요구(EXECUTE grant·Resource Principal·Data Access 등) 신호등 점검 + 원클릭 적용
3. **프로파일** (`/profiles`) — 21개 속성 한국어 해설 폼 + 대상 테이블(`object_list`) 선택 + `CREATE_PROFILE` 미리보기
4. **플레이그라운드** (`/playground`) — runsql/showsql/explainsql/narrate/chat 액션 비교
5. **챗봇** (`/chat`) — 멀티턴 대화 + 맥락 유무 비교
6. **증강 비교** (`/enrichment`) — 모호 스키마에 COMMENT를 더했을 때 NL2SQL 정확도가 달라지는 전/후 비교 (데모 클라이맥스)
7. **설정** (`/settings`) — 기본 프로파일, 표시 모드, **데모 환경 정리**(생성한 리소스 일괄 정리)

> 화면 하단의 **SQL 로그 터미널**(VS Code 스타일, `Ctrl/Cmd+\``)에 DB에서 실행된 모든 SQL이 시계열로 누적되어, "지금 이 클릭이 무엇을 실행했는가"를 그대로 보여줍니다.

## 환경변수

`backend/.env.example`를 복사해 사용합니다. 비밀번호는 `.env`가 아니라 `~/.selectai/connections.json`에 Fernet 암호화로 저장됩니다.

```bash
cp backend/.env.example backend/.env   # 필요 시 값 조정
```

주요 항목: `APP_SECRET_KEY`(미설정 시 `~/.selectai/secret.key` 자동 생성), `APP_DATA_DIR`, `DEFAULT_OCI_COMPARTMENT_ID`(TAEWAN.KIM), `DEFAULT_OCI_REGION`, `DEFAULT_MODEL`, `SELECTAI_CALL_TIMEOUT_MS`.

## 테스트

```bash
cd backend  && uv run pytest -q                 # 백엔드 단위 테스트 (oracledb 모킹, 실 DB 불필요)
cd frontend && npx tsc --noEmit && npm run build # 프론트 타입 검사 + 빌드
```

백엔드 테스트는 읽기 전용 게이트(LLM 생성 SQL의 비SELECT 자동 차단), `GENERATE` 바인드 패턴, 자격 암호화·마스킹, wallet 검증 등 핵심 불변 규칙을 검증합니다.

## 보안 주의 (데모 도구)

- 프로덕션급 보안은 비목표입니다. 단 `admin` 비밀번호·wallet은 `~/.selectai/`(권한 0700)에 Fernet 암호화로 저장하고 로그·응답·SQL 미리보기에서 마스킹합니다.
- LLM이 생성한 SQL 중 비SELECT(INSERT/UPDATE/DELETE/DDL)는 앱 계층에서 **자동 차단**됩니다(수동 오버라이드 없음).
- 고객 환경 시연 후에는 **설정 → 데모 환경 정리**로 앱이 생성한 프로파일·credential·대화·데모 테이블을 일괄 제거하세요.

## 문서 맵

[`docs/INDEX.md`](docs/INDEX.md)에서 전체 설계 문서(PRD·아키텍처·API 명세·보안·데모 시나리오·스타일·기술 근거)로 이동할 수 있습니다.
