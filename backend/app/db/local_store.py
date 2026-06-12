"""JSON 파일 저장소 — ~/.selectai/{connections,settings,resources}.json.

architecture.md §3.3: 임시 파일 작성 후 os.replace 원자적 교체 + 파일별
asyncio.Lock. 디렉토리 0700, 파일 0600. SQLite 미사용 — JSON 파일 저장소만.

구현 담당: 저장소/보안 에이전트.
"""
