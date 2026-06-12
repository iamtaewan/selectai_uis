"""커넥션 풀 레지스트리 — connection_id → oracledb.AsyncConnectionPool.

architecture.md §3.2: 저장 커넥션 1개당 풀 1개 (min=0, max=4, increment=1,
getmode=POOL_GETMODE_WAIT, wait_timeout=10s). lazy 생성 + 30분 유휴 close.
세션 상태를 남기는 호출 금지 (SET_PROFILE/SET_CONVERSATION_ID — 원칙 1).

구현 담당: DB/커넥션 에이전트.
"""
