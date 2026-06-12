"""권한 점검 서비스 — 선언적 점검 카탈로그, 적용 SQL 생성(미리보기=실행 동일 문자열).

근거: architecture.md §3.4, api-spec §3, selectai-reference.md §4.
build_sql(...) -> ExecutableSql(sql, binds, redacted_sql) 패턴 준수.

구현 담당: 권한 에이전트.
"""
