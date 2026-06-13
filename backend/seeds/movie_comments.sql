-- movie_comments.sql — COMMENT ON TABLE/COLUMN 증강 세트 (selectai-reference.md §7 p147-149 원문 패턴)
-- 모호한 컬럼명(c1~c7)에 비즈니스 의미를 부여한다 — comments:"true" 프로파일이 이 메타데이터를 LLM에 전송.
-- 리터럴 내 작은따옴표는 '' 이중화 (api-spec §1.6).

COMMENT ON TABLE table1 IS 'Contains movies, movie titles and the year it was released';
COMMENT ON COLUMN table1.c1 IS 'movie ids. Use this column to join to other tables';
COMMENT ON COLUMN table1.c2 IS 'movie titles';
COMMENT ON COLUMN table1.c3 IS 'year the movie was released';

COMMENT ON TABLE table2 IS 'Movie watch history: when a movie was watched and how many times it was viewed or streamed';
COMMENT ON COLUMN table2.c1 IS 'movie ids. Use this column to join to other tables';
COMMENT ON COLUMN table2.c6 IS 'date the movie was watched';
COMMENT ON COLUMN table2.c7 IS 'number of views, watched, streamed';

COMMENT ON TABLE table3 IS 'Devices and users that watched movies';
COMMENT ON COLUMN table3.c1 IS 'movie ids. Use this column to join to other tables';
COMMENT ON COLUMN table3.c4 IS 'device type used to watch the movie, such as smart tv, mobile, tablet, laptop';
COMMENT ON COLUMN table3.c5 IS 'user name who watched the movie';
