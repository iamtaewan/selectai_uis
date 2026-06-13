"""Fernet 암호화 + 로그 마스킹 필터 — security.md §2 기준 최소선.

- 키: APP_SECRET_KEY 환경변수 우선, 없으면 ~/.selectai/secret.key 자동 생성(0600) + 경고 로그.
- 평문 폴백 금지 — 키 없이는 저장하지 않는다 (security.md §2.1 불변 조건).
- 키 회전·OCI Vault 연동은 비목표 — 구현하지 않는다.
- 로그 마스킹: password/wallet_password/private_key/api_token/--password 값과
  Fernet 토큰 패턴을 ***MASKED***로 치환 (api-spec §1.5 규칙 2, security.md §2.3).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger("selectai.crypto")

MASK = "***MASKED***"

# 마스킹 패턴 — 로그·executed_sql·오류 detail 공통 적용 (security.md §2.3 표)
_MASK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OCI CLI: --password <값> / --password=<값> (api-spec §2.7)
    (
        re.compile(r"(--password)([ =]+)(?:\"[^\"]*\"|'[^']*'|\S+)"),
        r"\1\2" + MASK,
    ),
    # key: value / key=value / key => value (JSON·SQL·로그 공통) — 비밀 키 이름 목록
    (
        re.compile(
            r"(?i)([\"']?(?:password|wallet_password|private_key|api_token)[\"']?"
            r"\s*(?:=>|[:=])\s*)(?:\"[^\"]*\"|'[^']*'|\S+)"
        ),
        r"\1" + MASK,
    ),
    # Fernet 토큰 (버전 바이트 0x80 → 'gAAAA' 프리픽스)
    (re.compile(r"gAAAA[A-Za-z0-9_\-]{16,}={0,2}"), MASK),
]


def mask_secrets(text: str) -> str:
    """문자열 내 비밀값을 ***MASKED***로 치환한다 (멱등)."""
    masked = text
    for pattern, repl in _MASK_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked


class SecretMaskingFilter(logging.Filter):
    """logging Filter — 포매팅된 메시지에 마스킹을 적용한다 (security.md §2.3)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # 포매팅 실패 시 원본 유지 (마스킹 불가보다 로그 유실이 낫지 않음)
            return True
        masked = mask_secrets(message)
        if masked != message:
            record.msg = masked
            record.args = None
        return True


_MASKING_INSTALLED = False


def install_log_masking() -> None:
    """루트·uvicorn 로거에 마스킹 필터를 1회 설치한다 (멱등)."""
    global _MASKING_INSTALLED
    if _MASKING_INSTALLED:
        return
    masking_filter = SecretMaskingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "selectai"):
        target = logging.getLogger(name)
        target.addFilter(masking_filter)
        for handler in target.handlers:
            handler.addFilter(masking_filter)
    _MASKING_INSTALLED = True


# 모듈 임포트 시점에 설치 — main.py를 수정하지 않고 전역 마스킹 보장 (병렬 작업 규칙)
install_log_masking()


def _key_file_path():
    """secret.key 경로 — 앱 데이터 디렉토리(0700) 아래 0600."""
    return get_settings().data_dir / "secret.key"


def _normalize_key(raw: str) -> bytes:
    """APP_SECRET_KEY 값을 Fernet 키로 정규화한다.

    유효한 Fernet 키(urlsafe base64 32바이트)면 그대로 사용하고,
    아니면 SHA-256으로 결정적 파생한다 (임의 passphrase 허용 — 설치 간편성).
    """
    candidate = raw.strip().encode()
    try:
        Fernet(candidate)
        return candidate
    except (ValueError, TypeError):
        digest = hashlib.sha256(raw.encode()).digest()
        return base64.urlsafe_b64encode(digest)


def load_or_create_key() -> bytes:
    """마스터 키 로드 — APP_SECRET_KEY 우선, 없으면 secret.key 자동 생성(0600).

    키-데이터 분리·평문 폴백 금지 (security.md §2.1 X1 결정). 키 회전 미지원(비목표).
    """
    settings = get_settings()
    if settings.app_secret_key:
        return _normalize_key(settings.app_secret_key)

    key_path = _key_file_path()
    if key_path.exists():
        return key_path.read_bytes().strip()

    # 최초 기동: 디렉토리 0700 + 키 파일 0600 자동 생성, 콘솔 경고 (X1 결정)
    key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(key_path.parent, 0o700)
    key = Fernet.generate_key()
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fp:
        fp.write(key)
    logger.warning(
        "APP_SECRET_KEY 미설정 — %s 에 마스터 키를 자동 생성했습니다(0600). "
        "이 파일을 삭제하면 저장된 자격증명을 복호화할 수 없습니다.",
        key_path,
    )
    return key


def get_fernet() -> Fernet:
    """Fernet 인스턴스 — 키는 호출 시점 로드(테스트의 데이터 디렉토리 격리 지원)."""
    return Fernet(load_or_create_key())


def encrypt_secret(plaintext: str) -> str:
    """비밀값을 Fernet 토큰(str)으로 암호화한다."""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Fernet 토큰을 복호화한다. 키 불일치 시 사용자 친화 오류로 변환."""
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise AppError(
            status_code=500,
            code="SECRET_KEY_MISMATCH",
            app_code="SECRET_KEY_MISMATCH",
            message_ko="저장된 자격증명을 복호화할 수 없습니다. 마스터 키가 변경된 것 같습니다.",
            hint_ko="APP_SECRET_KEY 또는 ~/.selectai/secret.key가 저장 당시와 동일한지 확인하세요. "
            "복구가 불가능하면 커넥션을 삭제 후 다시 등록하세요.",
        ) from exc
