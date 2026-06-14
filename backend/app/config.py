"""앱 설정 — 환경변수 로딩 (architecture.md §6.3 기준).

비밀값(DB 비밀번호 등)은 환경변수가 아니라 ~/.selectai/connections.json에
Fernet 암호화로 저장한다 (§3.3). 여기에는 키·기본값만 둔다.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """환경변수 설정 (deploy/.env.example과 1:1)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 앱 일반
    app_env: str = "local"                       # local / prod (로그 레벨·문서 노출 제어)
    app_secret_key: str | None = None            # Fernet 키 — 미설정 시 secret.key 자동 생성
    app_data_dir: Path = Path("~/.selectai")     # 앱 데이터 디렉토리 (wallets/·JSON·secret.key)

    # OCI CLI (wallet 자동 다운로드 §3.1.1)
    oci_cli_profile: str = "DEFAULT"

    # DB 풀/타임아웃
    db_pool_max: int = 4
    db_call_timeout_ms: int = 15_000             # 일반 쿼리 call_timeout
    selectai_call_timeout_ms: int = 120_000      # GENERATE 계열 call_timeout 상한

    # 프로파일 기본값 (api-spec §4.1 defaults)
    # 컴파트먼트 OCID는 환경변수 DEFAULT_OCI_COMPARTMENT_ID(또는 .env)로 주입 — 코드 하드코딩 금지.
    default_oci_compartment_id: str = ""
    default_oci_region: str = "us-chicago-1"
    default_model: str = "meta.llama-3.3-70b-instruct"

    # 대화 기본 보관일 (오픈 이슈 O4)
    conversation_retention_days: int = 7

    @property
    def data_dir(self) -> Path:
        """~ 확장된 앱 데이터 디렉토리 경로."""
        return self.app_data_dir.expanduser()


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴 (FastAPI 의존성 주입용)."""
    return Settings()
