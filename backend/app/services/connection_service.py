"""커넥션 서비스 — wallet 해제/검증, TNS alias 추출, OCI CLI 자동 다운로드, 풀 수명주기.

근거: architecture.md §3.1·§3.1.1, api-spec §2. OCI CLI는 asyncio subprocess 비차단
실행, --password는 ***MASKED*** 처리. 기본 컴파트먼트는 TAEWAN.KIM OCID.

구현 담당: 커넥션 에이전트.
"""
