# 보안 설계 — Select AI Demo Studio

| 항목 | 내용 |
|---|---|
| 문서 | `docs/security.md` v1.0 (2026-06-12) |
| 작성자 | 보안 엔지니어 (전문가 7/8) |
| 상위 문서 | `PRD.md` (FR-01~09, 리스크 R5), `docs/research/selectai-reference.md` (기술 근거) |
| 적용 범위 | 데모 애플리케이션 (프로덕션 아님). 단, **고객 환경(고객 ADB·고객 데이터)에서 시연**되므로 자격증명·고객 데이터 보호는 타협 불가 |

> **설계 철학**: PRD §2.2가 명시했듯 SSO·감사 로그·비밀 관리 서비스 연동은 비목표다. 본 문서는 "데모 도구가 고객 환경에서 사고를 내지 않기 위한 최소선이자 충분선"을 정의한다. 모든 Select AI 기술 사실(프로시저명·속성명·권한 SQL)은 `docs/research/selectai-reference.md`(이하 "레퍼런스")만을 근거로 한다.

---

## 1. 위협 모델 요약

### 1.1 보호 자산 (우선순위순)

| # | 자산 | 노출 시 영향 | 주 위협 경로 |
|---|---|---|---|
| A1 | **ADB `admin` 비밀번호** | 고객 DB 전체 장악 (admin은 최고 권한 사용자) | 평문 저장 파일 유출, 로그/에러 메시지 노출, API 응답 에코 |
| A2 | **mTLS wallet (zip 및 해제 파일)** | DB 네트워크 접속 자격 — 비밀번호와 결합 시 A1과 동급 | 업로드 디렉토리 방치, 백업/복사, 데모 종료 후 잔존 |
| A3 | **OCI 자격증명** (API 서명 private key / `DBMS_CLOUD.CREATE_CREDENTIAL` 입력값) | 테넌시 OCI GenAI 호출 비용·권한 남용 | UI 입력값 로깅, SQL 미리보기에 private_key 원문 포함 |
| A4 | **고객 데이터** (시연 대상 스키마의 실데이터) | 고객 정보 유출 — `narrate`는 실제 행 데이터를 LLM에 전송함 (레퍼런스 §7: SQL 생성 시에는 스키마 메타데이터만 전송, narrate만 예외, p14) | 데이터 액세스 미통제 상태에서 민감 테이블 narrate, object_list 미제한 |
| A5 | **앱이 생성한 DB 부산물** (프로파일, credential, ACL, 대화 이력, 데모 스키마) | 데모 후 고객 DB에 잔존하는 자격·이력 | 정리 누락 (§6 체크리스트로 대응) |

### 1.2 위협 시나리오와 수용/비수용 판단

| 시나리오 | 판단 | 근거/대응 |
|---|---|---|
| 같은 머신의 다른 로컬 사용자가 저장 파일 열람 | **대응** | at-rest 암호화 (§2) |
| 네트워크상의 제3자가 API 트래픽 도청 | **대응** | localhost 바인딩(로컬), HTTPS(배포) (§5) |
| 시연자 본인의 악의 | **수용** (비목표) | 단일 시연자 도구 — 사용자 계정/감사 체계 없음 (PRD §2.2) |
| LLM이 파괴적 SQL(DML/DDL) 생성 후 runsql로 실행 | **대응** | 실행 전 SQL 표시·읽기 전용 게이트 (§3) |
| LLM 공급자(OCI GenAI)로의 데이터 전송 자체 | **부분 수용** | OCI GenAI는 고객 테넌시 내 서비스. 단 narrate의 실데이터 전송은 명시 고지 + Data Access 제어 시연 (§4) |
| 데모 앱 서버 취약점으로 원격 침투 | **부분 대응** | 인터넷 비공개 원칙, 최소 포트 (§5). WAF·IDS는 비목표 |

---

## 2. 자격증명 관리 (A1, A2, A3)

### 2.1 저장: at-rest 암호화 (FR-02 "자격 암호화 저장"의 구체화)

- **암호화 방식**: 대칭키 인증 암호화(AEAD; 예: Fernet 또는 AES-256-GCM)로 다음을 암호화하여 저장한다.
  - `admin` 비밀번호 (커넥션 레코드 필드)
  - wallet zip 원본 바이트 (또는 해제 디렉토리 전체)
  - 저장이 필요한 OCI credential 입력값 (private_key 등 — 가능하면 **저장하지 않고 일회성 입력 후 폐기**가 기본)
- **마스터 키 관리** (X1 결정): 앱 마스터 키는 환경 변수 `APP_SECRET_KEY`를 **우선** 사용하고, 미설정 시 최초 기동에서 권한 600의 `~/.selectai/secret.key`를 **자동 생성**하되 콘솔에 경고를 출력한다. 암호화 데이터(`connections.json`)와 키 파일은 **별도 파일**로 분리하며, 키 없이 평문으로 저장하는 폴백은 **금지**한다 (자동 생성은 허용하되 평문 폴백은 불허 — 데모 도구의 설치 간편성과 최소 보안선을 동시에 충족). **키 회전 정책과 OCI Vault 연동은 데모 도구 범위 외(비목표)** — 도입하지 않는다. "키-데이터 분리, 평문 폴백 금지" 두 원칙은 불변 조건이다.
- **파일 권한**: 앱 데이터 디렉토리 `~/.selectai/`는 `0700`, 그 하위의 wallet 디렉토리(`~/.selectai/wallets/{wallet_id}/`)도 `0700`, 저장소 파일·키 파일은 `0600`/`0700` (소유자 전용 — architecture.md §3.3). 업로드 임시 파일은 OS 공용 tmp가 아닌 앱 전용 디렉토리에 생성한다. wallet 자동 다운로드(OCI CLI 경로, architecture.md §3.1.1)로 받은 zip도 동일 위치·동일 권한으로 보관 후 평문 zip은 즉시 삭제한다.

### 2.2 메모리·전송 중 처리

- wallet zip은 업로드 직후 검증(FR-01: zip 구조, `tnsnames.ora` 존재)하고, 접속에 필요한 동안만 해제 상태로 유지한다. 해제 경로는 커넥션별 격리 디렉토리를 사용한다.
- `admin` 비밀번호는 python-oracledb 연결 파라미터로 전달하는 순간 외에는 복호화 상태로 보관하지 않는다 (요청 스코프 내 사용 후 참조 해제).
- API 요청에서 비밀번호는 body로만 받는다 (URL 쿼리스트링 금지 — 액세스 로그에 남는다).

### 2.3 절대 로그·응답에 남기지 않을 항목 (마스킹 목록)

다음 항목은 **애플리케이션 로그, uvicorn/액세스 로그, 예외 트레이스백, API 응답, 그리고 "실행 SQL 미리보기"(design.md 설계 전제 5)** 어디에도 평문 노출이 금지된다.

| 항목 | 마스킹 규칙 |
|---|---|
| `admin` 비밀번호 | 전 구간 `********`. API 응답의 커넥션 객체에 비밀번호 필드 자체를 포함하지 않음 (FR-01 수용 기준) |
| wallet zip 비밀번호(있는 경우) | 동일 |
| wallet 자동 다운로드의 wallet 암호 (OCI CLI `generate-wallet --password`) | **실행된 CLI 명령을 로그/응답(`executed_sql`)에 노출할 때 `--password` 값은 `***MASKED***`** (api-spec §2.7). subprocess 인자 로깅에도 동일 필터 적용 |
| OCI `private_key` | SQL 미리보기에서 `private_key => '<masked>'`로 표시. **CREATE_CREDENTIAL 호출 SQL만은 미리보기에 원문 대신 마스킹본을 노출** — 학습 효과(설계 전제 5)보다 A3 보호가 우선 |
| 외부 공급자 API 키 (`CREATE_CREDENTIAL`의 `password`) | 동일 마스킹 |
| `fingerprint`, `user_ocid`, `tenancy_ocid` | 유출 단독 위험은 낮으나 로그에는 뒷자리 일부만 표시 권장 |

- 구현 강제 수단: 백엔드에 **중앙 마스킹 필터**(logging Filter + 응답 직렬화 시 secret 타입 필드 제외)를 두고, DB 오류(ORA-)를 사용자에게 전달할 때도 바인드 값이 포함된 원문은 필터를 통과시킨다.
- python-oracledb 디버그/트레이스 옵션은 기본 비활성으로 한다 (연결 문자열·자격 노출 가능).

### 2.4 세션 종료·커넥션 삭제 시 정리

- 커넥션 삭제(FR-02) 시: 암호화된 자격 레코드 + wallet zip + 해제 디렉토리(`~/.selectai/wallets/{wallet_id}/`)를 함께 삭제한다.
- 앱 정상 종료 시: 해제 상태의 wallet 임시 디렉토리를 삭제한다 (암호화 원본만 유지).
- 비정상 종료 대비: 앱 기동 시 고아 임시 디렉토리를 스캔·정리한다.

### 2.5 OCI CLI 인증 (`~/.oci`) — 앱 비관리 원칙

wallet 자동 다운로드(architecture.md §3.1.1, api-spec §2.7)는 시연자 로컬의 OCI CLI와 `~/.oci/config` 인증 구성을 그대로 사용한다.

- **앱은 `~/.oci`의 키·설정을 읽기/저장/수정하지 않는다.** OCI CLI 인증 구성(API 키 생성·프로파일 관리·키 회전)은 전적으로 **시연자 로컬 책임**이다 — 앱의 자격 저장소(§2.1)와 보호 범위를 분리한다.
- 앱이 CLI에 전달하는 비밀은 wallet 암호(`--password`) 하나뿐이며, §2.3 마스킹 목록에 따라 로그·응답에서 마스킹한다.
- CLI 인증 실패는 앱이 복구를 시도하지 않고 한국어 안내 + 수동 업로드 폴백으로 처리한다 (CLAUDE.md 전역 규칙에 따라 기본 컴파트먼트는 `TAEWAN.KIM`).

---

## 3. SQL 인젝션 및 생성 SQL 실행 통제 (NL2SQL 특유 위험)

### 3.1 위험 구조

이 앱은 두 종류의 SQL을 다룬다.

1. **앱이 조립하는 SQL/PLSQL** — `DBMS_CLOUD_AI.GENERATE(...)` 호출, 권한 점검 쿼리, COMMENT DDL 등.
2. **LLM이 생성한 SQL** — runsql 액션이 DB 내부에서 실행. 가이드 공식 경고대로 환각·오류 가능 (레퍼런스 §10-4, p14·p45). DB 사용자가 `admin`이므로 생성 SQL이 DML/DDL이면 이론상 무엇이든 실행될 수 있다.

### 3.2 통제 1 — 앱 조립 SQL: 바인드 변수 우선, 인용 이스케이프 보조

- `GENERATE` 호출은 **바인드 변수**로 작성한다 (문자열 포매팅으로 prompt를 SQL에 삽입 금지):

```python
cursor.execute(
    """SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => :prompt,
         profile_name => :profile_name,
         action       => :action,
         params       => :params) FROM dual""",
    prompt=user_prompt, profile_name=profile, action=action, params=params_json)
```

- 바인드가 불가능한 위치(객체명: 프로파일명, 테이블/컬럼명, COMMENT 대상 등)는 **화이트리스트 검증**을 적용한다: 식별자 패턴(`^[A-Za-z][A-Za-z0-9_$#]{0,127}$`) 검사 + 가능한 경우 `USER_OBJECTS`/딕셔너리 뷰 대조 후 인용 식별자로 조립.
- COMMENT 텍스트(FR-08)는 리터럴 위치이므로 작은따옴표 이스케이프(`'` → `''`)를 백엔드가 일괄 수행한다 — FR-06 수용 기준의 프롬프트 이스케이프와 동일 유틸리티 사용 (레퍼런스 §1, p45).
- "실행 SQL 미리보기"(설계 전제 5)는 **바인드 값이 치환된 표시용 문자열**을 별도 생성해 보여주되, 실제 실행은 항상 바인드 경로로 한다 (미리보기 문자열을 그대로 실행하는 구현 금지).

### 3.3 통제 2 — LLM 생성 SQL: 표시 → 확인 → 실행 게이트

- **기본 흐름 권고**: 액션 시연(FR-06)에서 `runsql` 실행 결과 화면에도 생성 SQL 원문을 함께 표시한다(`showsql` 응답과 동일 정보). 미지의 고객 스키마 대상 시연 시에는 "showsql 먼저 → 확인 후 runsql" 흐름을 UI가 권장 모드로 제공한다.
- **읽기 전용 게이트(필수)**: runsql/챗봇 턴이 반환·실행하는 **LLM 생성 SQL** 경로에 대해 백엔드가 SELECT 문 여부를 검사한다. SELECT 외 구문(INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE 등)이 감지되면 **수동 오버라이드 없이 자동 차단**하고, SQL 원문과 경고만 표시한다(실행 버튼 비활성). 이 경로에는 "확인 후 강제 실행" 옵션을 두지 않는다 — 프롬프트 인젝션이 사용자 확인 클릭을 유도할 수 있기 때문이다. (admin 접속 확정 사항에 대한 보상 통제 — DB 계정 권한 축소가 불가능하므로 앱 계층에서 전면 차단)
- **앱이 의도적으로 실행하는 DDL의 격리**: FR-08 데모 스키마 생성, COMMENT 적용, FR-03 grant 적용은 LLM 생성 SQL과 분리된 **고정 템플릿 + 식별자 화이트리스트** 경로로만 실행하며, 모두 실행 전 SQL 미리보기 + 사용자 확인 클릭을 거친다 (FR-03 수용 기준과 일치).
- 챗봇(FR-07)의 기본 액션은 `narrate`/`chat`이며, 대화 중 `runsql` 선택 시에도 동일 게이트를 적용한다.

### 3.4 통제 3 — 프롬프트 인젝션 인지

- 자연어 프롬프트로 "drop table을 만들어 달라"는 식의 유도(직접 또는 COMMENT 텍스트를 통한 간접 주입)가 가능하다. §3.3의 읽기 전용 게이트는 LLM 생성 SQL 경로의 비SELECT 구문을 수동 오버라이드 없이 전면 차단하므로, 인젝션이 사용자 확인 클릭을 유도하더라도 파괴적 SQL이 실행되지 않는다. COMMENT 입력 폼에는 "코멘트는 LLM 프롬프트에 포함된다"는 안내를 표시한다 (comments=true 시 증강 프롬프트에 포함됨 — 레퍼런스 §7).

---

## 4. Select AI 데이터 액세스 제어 (A4 — 고객 데이터 보호)

레퍼런스가 제공하는 DB 측 통제 3종을 앱 기능으로 흡수한다.

### 4.1 Data Access ENABLE/DISABLE (레퍼런스 §2, p174–176)

- `DBMS_CLOUD_AI.DISABLE_DATA_ACCESS` (ADMIN 실행): LLM으로의 **실데이터 전송 차단**. 이 상태에서 `narrate`·합성 데이터는 `ORA-20000: Data access is disabled for SELECT AI`로 실패하고, NL2SQL(runsql/showsql)은 계속 동작한다.
- 앱 정책:
  - FR-03 점검 항목에 현재 상태를 표시하고(PRD FR-03), `ENABLE_DATA_ACCESS` 원클릭 복구를 제공한다.
  - **반대로 민감 데이터 환경에서는 DISABLE 상태가 "보안 기능"이다.** 점검 화면은 이를 오류가 아니라 "거버넌스 선택"으로 설명하고, 양방향 토글을 제공한다 (P1: Data Access ON/OFF 거버넌스 시연 — PRD §8).
  - narrate/챗봇 화면에 상시 안내: "narrate는 쿼리 결과(실데이터)를 LLM에 전송합니다. SQL 생성 자체는 스키마 메타데이터만 전송합니다." (레퍼런스 §7, p14)

### 4.2 object_list로 노출 스키마 최소화 (레퍼런스 §3)

- 프로파일 `object_list`를 **항상 명시**하도록 UI가 유도한다. 미지정 시 현재 스키마의 모든 객체가 자동 선택되며(레퍼런스 §3, p78·p151), admin 접속 특성상 의도치 않은 광범위 메타데이터 노출로 이어진다 → 프로파일 생성 폼(FR-04)에서 object_list 미선택 시 경고 표시.
- 시연용 프로파일은 데모 스키마(SH, 무비 모호 스키마)로 object_list를 한정하는 것을 기본 템플릿으로 한다.

### 4.3 enforce_object_list (레퍼런스 §3, p190–191)

- `"enforce_object_list": "true"`면 LLM이 object_list에 나열된 테이블만 사용하도록 제한된다. 고객 실스키마 대상 시연 프로파일에는 이 속성을 켜는 것을 권장 기본값으로 제시한다 (FR-04 폼에서 보안 권장 배지 표시).

### 4.4 대화 이력의 데이터 잔존

- Conversations는 영구 테이블에 저장된다 (레퍼런스 §6). 고객 데이터가 포함된 narrate 응답이 `USER_CLOUD_AI_CONVERSATION_PROMPTS`에 남으므로:
  - 새 대화 기본값에 짧은 `retention_days`를 적용한다 (O4 결정: 기본 7일, 자동 삭제 없음·수동 일괄 삭제 제공 — architecture.md §5.2, api-spec §6.1).
  - 데모 종료 정리(§6)에 `DROP_CONVERSATION` 포함.

---

## 5. 네트워크 보안

### 5.1 로컬 개발/시연 (기본)

- FastAPI(uvicorn)와 React dev 서버 모두 **`127.0.0.1` 바인딩** 기본값. `0.0.0.0` 바인딩은 명시적 플래그로만 허용하고, 사용 시 기동 로그에 경고를 출력한다.
- DB 연결은 mTLS wallet 기반이므로 앱→ADB 구간은 wallet의 TLS로 보호된다 (확정 사항).
- CORS는 프론트엔드 origin(`http://localhost:<port>`)만 허용.

### 5.2 OCI Compute 배포 시

- **HTTPS 필수**: reverse proxy(nginx/caddy) 뒤에 FastAPI를 두고 TLS 종단. 앱 포트(8000 등)는 localhost에만 바인딩하고 proxy만 노출 (배포 형태 상세는 오픈 이슈 O5 — 단 "HTTP 평문으로 admin 비밀번호 전송 금지"는 불변 조건).
- **OCI Security List / NSG 최소 개방**: 인바운드는 443(HTTPS)과 관리용 22(SSH, 가급적 운영자 IP CIDR 한정)만. 그 외 전부 차단. 모든 네트워크 리소스는 `TAEWAN.KIM` 컴파트먼트(`ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq`) 내에 생성한다.
- **인터넷 전면 공개 금지 권고**: 인증 체계가 없는 단일 시연자 도구이므로, 공개가 불가피하면 최소한 reverse proxy Basic Auth 또는 소스 IP 제한을 적용한다 (앱 자체 인증 기본값은 오픈 이슈 O1과 함께 architecture.md에서 확정).
- Resource Principal 사용 시(레퍼런스 §4.4) Dynamic Group 정책은 `manage generative-ai-family`를 **테넌시 전체가 아닌 컴파트먼트 한정**으로 작성한다:

```text
allow dynamic-group <dynamic-group-name> to manage generative-ai-family in compartment TAEWAN.KIM
```

---

## 6. 데모 후 정리 체크리스트 (A5)

데모 종료 시 고객 DB와 시연 머신에 남는 부산물을 제거한다. 앱은 이 체크리스트를 PG-08 "데모 환경 정리(Cleanup)" 섹션으로 제공하고, 각 항목 실행 전 SQL/파일 작업 미리보기를 표시한다. 정리 대상은 앱이 `~/.selectai/resources.json`에 기록한 생성 리소스 대장(ledger)을 기준으로 조회한다 (`GET /api/v1/resources`, `DELETE /api/v1/resources/{id}`, `POST /api/v1/resources/cleanup`). 대장 파일 자체에는 비밀값(비밀번호·private key)을 기록하지 않으며, `cleanup_sql`의 자격 관련 값은 마스킹된 형태로 보관한다. 모든 SQL은 레퍼런스 §2·§5 근거.

### 6.1 DB 측 정리 SQL

```sql
-- 1) 대화 정리: 목록 확인 후 전체 삭제 (narrate 응답에 고객 데이터 잔존 가능 — §4.4)
SELECT conversation_id, conversation_title FROM USER_CLOUD_AI_CONVERSATIONS;
EXEC DBMS_CLOUD_AI.DROP_CONVERSATION('<conversation_uuid>');   -- 대화별 반복

-- 2) 프로파일 삭제 (앱이 생성한 프로파일 전부 — comments off/on 쌍 포함)
SELECT profile_name FROM USER_CLOUD_AI_PROFILES;
EXEC DBMS_CLOUD_AI.DROP_PROFILE('<profile_name>');             -- 프로파일별 반복

-- 3) 자격증명 삭제 (API 서명 키 credential을 만들었던 경우)
EXEC DBMS_CLOUD.DROP_CREDENTIAL('<credential_name>');

-- 4) 네트워크 ACL 회수 (외부 공급자를 시연했던 경우에만 — OCI GenAI만 썼다면 해당 없음)
BEGIN
  DBMS_NETWORK_ACL_ADMIN.REMOVE_HOST_ACE(
    host => 'api.openai.com',   -- 적용했던 공급자 host (레퍼런스 §4.2 host 목록)
    ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                        principal_name => '<grantee_user>',
                        principal_type => xs_acl.ptype_db));
END;
/

-- 5) 시연용으로 일반 사용자에게 부여했던 grant 회수 (FR-03 "시연용 grant 위저드" 사용 시)
REVOKE EXECUTE ON DBMS_CLOUD_AI FROM <ADB_USER>;
REVOKE EXECUTE ON DBMS_CLOUD_PIPELINE FROM <ADB_USER>;          -- RAG 시연 시
REVOKE READ ON SYS.V_$MAPPED_SQL FROM <ADB_USER>;               -- feedback(P1) 시연 시
REVOKE READ ON SYS.V_$SESSION FROM <ADB_USER>;

-- 6) 데모 모호 스키마 제거 (FR-08 원클릭 생성분)
DROP TABLE <demo_table1> PURGE;   -- 앱이 생성한 테이블 목록 기준 (table1~3 등)

-- 7) Data Access 상태를 데모 이전 값으로 원복 (앱이 변경했던 경우 — §4.1)
EXEC DBMS_CLOUD_AI.ENABLE_DATA_ACCESS;    -- 또는 DISABLE_DATA_ACCESS (원래 상태 기준)
```

> 주의: feedback(P1)·automated object list(P2)를 시연한 경우 `<profile_name>_FEEDBACK_VECINDEX` / `<profile_name>_OBJECT_LIST_VECINDEX` 벡터 인덱스가 생성된다 (레퍼런스 §8). 프로파일 정리 시 `DBMS_CLOUD_AI.DROP_VECTOR_INDEX`로 함께 제거를 확인한다.

### 6.2 앱/시연 머신 측 정리

- [ ] 고객 환경용으로 등록한 커넥션 삭제 → 암호화 자격 레코드 + wallet zip + 해제 디렉토리 동반 삭제 확인 (§2.4)
- [ ] 앱 임시 디렉토리에 wallet 잔존 파일 없음 확인
- [ ] 앱 설정의 "기본 프로파일"(앱 수준 저장 — design.md 설계 전제 3)에서 고객 환경 프로파일 참조 제거
- [ ] (배포형) 데모 전용 Compute 인스턴스라면 인스턴스 정지/삭제, Security List 임시 개방분 원복

### 6.3 앱 변경 추적 전제

원클릭 정리는 **앱이 자신이 만든 리소스(프로파일·credential·ACL·대화·데모 테이블·grant·wallet 파일)를 로컬에 기록**한다는 전제 위에서 동작한다. 이 생성 리소스 대장(ledger)은 architecture.md §3.3.1의 `~/.selectai/resources.json` 모델과 api-spec.md §10 Resources CRUD API의 계약을 따른다.

- `GET /api/v1/resources`: `pending`/`failed` 정리 대상, 항목별 `cleanup_preview`, 의존성 순서 반환
- `DELETE /api/v1/resources/{id}`: 개별 항목 정리
- `POST /api/v1/resources/cleanup`: 선택 항목을 `cleanup_order` 순으로 정리하고 항목별 성공/실패를 기록
- 비밀값은 `create_sql`/`cleanup_sql`/응답 preview 어디에도 원문으로 남기지 않는다.

---

## 7. 구현 체크리스트 요약 (개발자용)

| # | 항목 | 관련 |
|---|---|---|
| S1 | 자격/wallet AEAD 암호화 저장, 마스터 키 분리, 평문 폴백 금지 | §2.1, FR-02 |
| S2 | 중앙 로그/응답 마스킹 필터 (비밀번호·private_key·API 키) | §2.3, FR-01 |
| S3 | SQL 미리보기에서 CREATE_CREDENTIAL 비밀값 마스킹 | §2.3, 설계 전제 5의 예외 |
| S4 | GENERATE 등 바인드 변수 실행 + 식별자 화이트리스트 + 리터럴 이스케이프 유틸 | §3.2, FR-06 |
| S5 | LLM 생성 SQL 읽기 전용 게이트 (비SELECT 자동 실행 차단) | §3.3 |
| S6 | object_list 미지정 경고 + enforce_object_list 권장 표시 | §4.2–4.3, FR-04 |
| S7 | narrate 실데이터 전송 고지 + Data Access 양방향 토글 | §4.1, FR-03 |
| S8 | 127.0.0.1 기본 바인딩, 배포 시 HTTPS + 443/22 최소 개방 | §5 |
| S9 | 생성 리소스 대장(resources.json) + `GET/DELETE/POST /api/v1/resources` + PG-08 원클릭 정리 화면 | §6 |
| S10 | 대화 retention_days 짧은 기본값 + 정리 시 DROP_CONVERSATION | §4.4, O4 |
| S11 | `~/.selectai` 0700 + OCI CLI 명령 로그의 `--password` 마스킹, `~/.oci` 비관리 | §2.1, §2.3, §2.5 |
