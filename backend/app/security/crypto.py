"""Fernet 암호화 + 로그 마스킹 필터 — security.md 기준 최소선.

- 키: APP_SECRET_KEY 환경변수, 없으면 ~/.selectai/secret.key 자동 생성 (0600).
- 키 회전·OCI Vault 연동은 비목표 — 구현 금지.
- logging Filter로 password/wallet_password/private_key/--password 값을
  ***MASKED***로 치환 (api-spec §1.5 규칙 2).

구현 담당: 저장소/보안 에이전트.
"""
