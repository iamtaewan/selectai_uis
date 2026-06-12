"""대화 서비스 — CREATE/UPDATE/DROP_CONVERSATION, 이력 뷰 조회, 맥락 비교 병렬 실행.

근거: api-spec §6, architecture.md §5. 대화 상태의 소유자는 ADB —
백엔드는 conversation_id를 저장하지 않고 통과시킨다 (stateless).

구현 담당: 챗봇 에이전트.
"""
