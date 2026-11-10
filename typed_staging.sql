SET client_min_messages = warning;
SET jit = off;

CREATE UNLOGGED TABLE IF NOT EXISTS pgdm_expansion_stage (
    raw_id bigint PRIMARY KEY,
    id1 integer,
    dt1 timestamp,
    t1 text,
    t2 text,
    t3 text,
    max_int2 smallint,
    num1 integer,
    num2 integer,
    int_1 text, int_2 text, int_3 text, int_4 text, int_5 text, int_6 text, int_7 text, int_8 text, int_9 text, int_10 text, int_11 text, int_12 text, int_13 text, int_14 text, int_15 text,
    txt_4 text, txt_5 text, txt_6 text, txt_7 text, txt_8 text, txt_9 text, txt_10 text, txt_11 text, txt_12 text, txt_13 text, txt_14 text, txt_15 text, txt_16 text, txt_17 text,
    num_3 text, num_4 text, num_5 text, num_6 text, num_7 text, num_8 text, num_9 text, num_10 text, num_11 text, num_12 text, num_13 text, num_14 text, num_15 text, num_16 text, num_17 text, num_18 text, num_19 text, num_20 text, num_21 text, num_22 text, num_23 text, num_24 text, num_25 text, num_26 text, num_27 text, num_28 text, num_29 text, num_30 text
);
TRUNCATE pgdm_expansion_stage;

INSERT INTO pgdm_expansion_stage
SELECT raw_id,
       NULLIF(BTRIM(id_column_1), '')::integer,
       NULLIF(BTRIM(datetime_column_1), '')::timestamptz AT TIME ZONE 'America/Sao_Paulo',
       text_column_1,
       text_column_2,
       text_column_3,
       GREATEST(NULLIF(BTRIM(integer_column_2), '')::smallint,
            NULLIF(BTRIM(integer_column_3), '')::smallint,
            NULLIF(BTRIM(integer_column_4), '')::smallint,
            NULLIF(BTRIM(integer_column_5), '')::smallint,
            NULLIF(BTRIM(integer_column_6), '')::smallint,
            NULLIF(BTRIM(integer_column_7), '')::smallint,
            NULLIF(BTRIM(integer_column_8), '')::smallint,
            NULLIF(BTRIM(integer_column_9), '')::smallint,
            NULLIF(BTRIM(integer_column_10), '')::smallint,
            NULLIF(BTRIM(integer_column_11), '')::smallint,
            NULLIF(BTRIM(integer_column_12), '')::smallint,
            NULLIF(BTRIM(integer_column_13), '')::smallint,
            NULLIF(BTRIM(integer_column_14), '')::smallint,
            NULLIF(BTRIM(integer_column_15), '')::smallint),
       CASE WHEN NULLIF(BTRIM(numeric_column_1), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_1), '')::numeric * 1000)::integer END,
       CASE WHEN NULLIF(BTRIM(numeric_column_2), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_2), '')::numeric * 1000)::integer END,
       integer_column_1, integer_column_2, integer_column_3, integer_column_4, integer_column_5, integer_column_6, integer_column_7, integer_column_8, integer_column_9, integer_column_10, integer_column_11, integer_column_12, integer_column_13, integer_column_14, integer_column_15,
       text_column_4, text_column_5, text_column_6, text_column_7, text_column_8, text_column_9, text_column_10, text_column_11, text_column_12, text_column_13, text_column_14, text_column_15, text_column_16, text_column_17,
       numeric_column_3, numeric_column_4, numeric_column_5, numeric_column_6, numeric_column_7, numeric_column_8, numeric_column_9, numeric_column_10, numeric_column_11, numeric_column_12, numeric_column_13, numeric_column_14, numeric_column_15, numeric_column_16, numeric_column_17, numeric_column_18, numeric_column_19, numeric_column_20, numeric_column_21, numeric_column_22, numeric_column_23, numeric_column_24, numeric_column_25, numeric_column_26, numeric_column_27, numeric_column_28, numeric_column_29, numeric_column_30
FROM (
    SELECT raw_id, v.*
    FROM public.raw_data
    CROSS JOIN LATERAL jsonb_to_record(raw -> 'values') AS v(
        id_column_1 text, text_column_1 text, text_column_2 text, text_column_3 text,
        text_column_4 text, text_column_5 text, text_column_6 text, text_column_7 text, text_column_8 text, text_column_9 text, text_column_10 text, text_column_11 text, text_column_12 text, text_column_13 text, text_column_14 text, text_column_15 text, text_column_16 text, text_column_17 text,
        integer_column_1 text, integer_column_2 text, integer_column_3 text, integer_column_4 text, integer_column_5 text, integer_column_6 text, integer_column_7 text, integer_column_8 text, integer_column_9 text, integer_column_10 text, integer_column_11 text, integer_column_12 text, integer_column_13 text, integer_column_14 text, integer_column_15 text,
        numeric_column_1 text, numeric_column_2 text, numeric_column_3 text, numeric_column_4 text, numeric_column_5 text, numeric_column_6 text, numeric_column_7 text, numeric_column_8 text, numeric_column_9 text, numeric_column_10 text, numeric_column_11 text, numeric_column_12 text, numeric_column_13 text, numeric_column_14 text, numeric_column_15 text, numeric_column_16 text, numeric_column_17 text, numeric_column_18 text, numeric_column_19 text, numeric_column_20 text, numeric_column_21 text, numeric_column_22 text, numeric_column_23 text, numeric_column_24 text, numeric_column_25 text, numeric_column_26 text, numeric_column_27 text, numeric_column_28 text, numeric_column_29 text, numeric_column_30 text,
        datetime_column_1 text
    )
    WHERE raw_schema IN ('group001')
) AS src;
ANALYZE pgdm_expansion_stage;

INSERT INTO public.table3 (text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4)
SELECT DISTINCT BTRIM(t1), 'SYNTHETIC/REFERENCE', NULL::numeric,
       LEFT(UPPER(BTRIM(t2)), 1), RIGHT(UPPER(BTRIM(t2)), 1)
FROM pgdm_expansion_stage s
WHERE BTRIM(t1) <> '' AND UPPER(BTRIM(t2)) ~ '^[A-Z]{2}$';

INSERT INTO public.table4 (id_column_1, text_column_1, text_column_2)
SELECT DISTINCT
       ((ASCII(LEFT(UPPER(BTRIM(t3)), 1)) - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(t3)), 1)) - ASCII('A') + 1)::smallint,
       'SYNTHETIC/GENERIC', UPPER(BTRIM(t3))
FROM pgdm_expansion_stage s
WHERE UPPER(BTRIM(t3)) ~ '^[A-Z]{2}$';

INSERT INTO public.table1
    (id_column_1, id_column_2, datetime_column_1, integer_column_1,
     integer_column_3, integer_column_7, id_column_3, id_column_4)
SELECT s.raw_id, s.id1, s.dt1, s.max_int2, s.num2, s.num1, s.raw_id,
       dimension_row.id_column_1
FROM pgdm_expansion_stage s
JOIN public.table3 AS dimension_row
  ON dimension_row.text_column_1 = BTRIM(s.t1)
 AND dimension_row.text_column_2 = 'SYNTHETIC/REFERENCE'
 AND dimension_row.numeric_column_1 IS NULL
 AND dimension_row.text_column_3 = LEFT(UPPER(BTRIM(s.t2)), 1)
 AND dimension_row.text_column_4 = RIGHT(UPPER(BTRIM(s.t2)), 1);

INSERT INTO public.table5 (numeric_column_1, id_column_2)
SELECT ROUND(NULLIF(BTRIM(s.int_1), '')::numeric, 1), s.raw_id
FROM pgdm_expansion_stage s
WHERE NULLIF(BTRIM(s.int_1), '')::numeric > 0;

INSERT INTO public.table6 (id_column_2, id_column_3)
SELECT s.raw_id, reference_row.id_column_1
FROM pgdm_expansion_stage s
JOIN public.table4 AS reference_row
  ON reference_row.text_column_1 = 'SYNTHETIC/GENERIC'
 AND reference_row.text_column_2 = UPPER(BTRIM(s.t3));

INSERT INTO public.table2
    (id_column_2, integer_column_1, integer_column_2, text_column_1, integer_column_6)
SELECT s.raw_id, p.position_number,
       ROUND(NULLIF(BTRIM(p.weight_text), '')::numeric * 1000)::integer,
       UPPER(BTRIM(p.type_text)),
       CASE WHEN NULLIF(BTRIM(p.gap_text), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(p.gap_text), '')::numeric * 1000)::integer END
FROM pgdm_expansion_stage s
CROSS JOIN LATERAL (VALUES
    (1::smallint, s.int_2, s.txt_4, s.num_3, s.num_4),
    (2::smallint, s.int_3, s.txt_5, s.num_4, s.num_5),
    (3::smallint, s.int_4, s.txt_6, s.num_5, s.num_6),
    (4::smallint, s.int_5, s.txt_7, s.num_6, s.num_7),
    (5::smallint, s.int_6, s.txt_8, s.num_7, s.num_8),
    (6::smallint, s.int_7, s.txt_9, s.num_8, s.num_9),
    (7::smallint, s.int_8, s.txt_10, s.num_9, s.num_10),
    (8::smallint, s.int_9, s.txt_11, s.num_10, s.num_11),
    (9::smallint, s.int_10, s.txt_12, s.num_11, s.num_12),
    (10::smallint, s.int_11, s.txt_13, s.num_12, s.num_13),
    (11::smallint, s.int_12, s.txt_14, s.num_13, s.num_14),
    (12::smallint, s.int_13, s.txt_15, s.num_14, s.num_15),
    (13::smallint, s.int_14, s.txt_16, s.num_15, s.num_16),
    (14::smallint, s.int_15, s.txt_17, s.num_16, s.num_17)
) AS p(position_number, declared_number_text, type_text, weight_text, gap_text)
WHERE NULLIF(BTRIM(p.declared_number_text), '')::smallint = p.position_number
  AND NULLIF(BTRIM(p.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(p.type_text)) IN ('X', 'Y', 'Z');

SELECT setval(pg_get_serial_sequence('public.table1', 'id_column_1'),
              COALESCE((SELECT max(id_column_1) FROM public.table1), 1), true);
DROP TABLE pgdm_expansion_stage;
