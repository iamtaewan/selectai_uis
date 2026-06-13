-- movie_schema.sql — FR-08 모호 스키마(c1~c7) 테이블 + 시드 데이터 (selectai-reference.md §7 ch19 패턴)
-- table1(c1,c2,c3)=movies / table2(c1,c6,c7)=watch history / table3(c1,c4,c5)=devices·users
-- 의도적으로 무의미한 컬럼명을 사용한다 — COMMENT 증강 전/후 비교 시연용.
-- 주의: COMMENT는 이 파일에 두지 않는다 (movie_comments.sql 전용 — "전" 상태 보장).

CREATE TABLE table1 (c1 NUMBER, c2 VARCHAR2(200), c3 NUMBER);

CREATE TABLE table2 (c1 NUMBER, c6 DATE, c7 NUMBER);

CREATE TABLE table3 (c1 NUMBER, c4 VARCHAR2(100), c5 VARCHAR2(100));

INSERT INTO table1 VALUES (1, 'The Godfather', 1972);
INSERT INTO table1 VALUES (2, 'Inception', 2010);
INSERT INTO table1 VALUES (3, 'Parasite', 2019);
INSERT INTO table1 VALUES (4, 'Interstellar', 2014);
INSERT INTO table1 VALUES (5, 'Oldboy', 2003);
INSERT INTO table1 VALUES (6, 'The Matrix', 1999);
INSERT INTO table1 VALUES (7, 'Spirited Away', 2001);
INSERT INTO table1 VALUES (8, 'Dune Part Two', 2024);
INSERT INTO table1 VALUES (9, 'Top Gun Maverick', 2022);
INSERT INTO table1 VALUES (10, 'The Dark Knight', 2008);

INSERT INTO table2 VALUES (1, DATE '2026-05-01', 120);
INSERT INTO table2 VALUES (1, DATE '2026-05-15', 95);
INSERT INTO table2 VALUES (2, DATE '2026-05-02', 340);
INSERT INTO table2 VALUES (2, DATE '2026-05-20', 410);
INSERT INTO table2 VALUES (3, DATE '2026-05-03', 560);
INSERT INTO table2 VALUES (3, DATE '2026-06-01', 480);
INSERT INTO table2 VALUES (4, DATE '2026-05-04', 290);
INSERT INTO table2 VALUES (5, DATE '2026-05-05', 150);
INSERT INTO table2 VALUES (6, DATE '2026-05-06', 380);
INSERT INTO table2 VALUES (7, DATE '2026-05-07', 270);
INSERT INTO table2 VALUES (8, DATE '2026-05-08', 720);
INSERT INTO table2 VALUES (8, DATE '2026-06-02', 650);
INSERT INTO table2 VALUES (9, DATE '2026-05-09', 530);
INSERT INTO table2 VALUES (10, DATE '2026-05-10', 460);
INSERT INTO table2 VALUES (10, DATE '2026-06-03', 390);

INSERT INTO table3 VALUES (1, 'smart tv', 'kim');
INSERT INTO table3 VALUES (2, 'mobile', 'lee');
INSERT INTO table3 VALUES (3, 'tablet', 'park');
INSERT INTO table3 VALUES (4, 'smart tv', 'choi');
INSERT INTO table3 VALUES (5, 'laptop', 'jung');
INSERT INTO table3 VALUES (6, 'mobile', 'kang');
INSERT INTO table3 VALUES (7, 'smart tv', 'cho');
INSERT INTO table3 VALUES (8, 'laptop', 'yoon');
INSERT INTO table3 VALUES (9, 'mobile', 'jang');
INSERT INTO table3 VALUES (10, 'tablet', 'lim');
