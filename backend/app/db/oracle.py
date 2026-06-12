"""쿼리 실행 헬퍼 — bind 실행, CLOB→str(fetch_lobs=False), call_timeout.

architecture.md §2.2 db 레이어: 도메인 지식 금지. 모든 SQL은 바인드 변수만 사용
(문자열 연결 금지). 타임아웃은 api-spec §12.2 표를 따른다.

구현 담당: DB/커넥션 에이전트.
"""
