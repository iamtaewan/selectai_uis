"""프로파일 서비스 — CREATE_PROFILE/SET_ATTRIBUTE(S)/DROP, 속성 화이트리스트 검증.

근거: api-spec §4, selectai-reference.md §3·§5. 식별자 검증
(^[A-Za-z][A-Za-z0-9_$#]{0,127}$) 후 사용, attributes JSON은 json.dumps 직렬화.

구현 담당: 프로파일 에이전트.
"""
