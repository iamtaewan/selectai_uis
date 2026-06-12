"""Select AI 실행 서비스 — GENERATE 단일 호출 경로 (latency 측정, runsql 2단계).

불변 규칙: DBMS_CLOUD_AI.GENERATE(prompt=>:1, profile_name=>:2, action=>:3,
params=>:4) 바인드만. params JSON은 json.dumps. SELECT AI 키워드·SET_PROFILE·
SET_CONVERSATION_ID 금지. runsql 2단계는 비SELECT 자동 차단 (security.md §3.3).

구현 담당: Select AI 에이전트.
"""
