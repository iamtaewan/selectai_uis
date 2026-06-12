"""리소스 대장 서비스 — resources.json ledger CRUD, cleanup 실행/파일 정리, 실패 격리.

근거: architecture.md §3.3.1, api-spec §10. cleanup_order 순 실행, 한 항목 실패해도
계속 진행. 대장 항목은 삭제하지 않고 cleanup_status만 갱신 (감사 기록 유지).

구현 담당: 리소스/대시보드 에이전트.
"""
