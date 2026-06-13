-- movie_reset.sql — 데모 테이블 정리 (Cleanup API·PG-08 보조)
-- DROP TABLE이 테이블/컬럼 COMMENT도 함께 제거한다. 미존재 테이블의 DROP 오류
-- (ORA-00942)는 enrichment_service가 무시한다. 비교용 프로파일 쌍(ENRICH_DEMO_OFF/ON)
-- 정리는 DBMS_CLOUD_AI.DROP_PROFILE 경로(서비스 코드)에서 수행한다.

DROP TABLE table1 PURGE;

DROP TABLE table2 PURGE;

DROP TABLE table3 PURGE;
