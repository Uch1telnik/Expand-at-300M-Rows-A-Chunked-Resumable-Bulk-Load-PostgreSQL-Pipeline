WITH src AS MATERIALIZED (
    SELECT raw_id, v.*
    FROM public.raw_data
    CROSS JOIN LATERAL jsonb_to_record(raw -> 'values') AS v(
        datetime_column_1 text,
        id_column_1 text,
        integer_column_1 text,
        integer_column_10 text,
        integer_column_11 text,
        integer_column_12 text,
        integer_column_13 text,
        integer_column_14 text,
        integer_column_15 text,
        integer_column_2 text,
        integer_column_3 text,
        integer_column_4 text,
        integer_column_5 text,
        integer_column_6 text,
        integer_column_7 text,
        integer_column_8 text,
        integer_column_9 text,
        numeric_column_1 text,
        numeric_column_10 text,
        numeric_column_11 text,
        numeric_column_12 text,
        numeric_column_13 text,
        numeric_column_14 text,
        numeric_column_15 text,
        numeric_column_16 text,
        numeric_column_17 text,
        numeric_column_18 text,
        numeric_column_19 text,
        numeric_column_2 text,
        numeric_column_20 text,
        numeric_column_21 text,
        numeric_column_22 text,
        numeric_column_23 text,
        numeric_column_24 text,
        numeric_column_25 text,
        numeric_column_26 text,
        numeric_column_27 text,
        numeric_column_28 text,
        numeric_column_29 text,
        numeric_column_3 text,
        numeric_column_30 text,
        numeric_column_4 text,
        numeric_column_5 text,
        numeric_column_6 text,
        numeric_column_7 text,
        numeric_column_8 text,
        numeric_column_9 text,
        text_column_1 text,
        text_column_10 text,
        text_column_11 text,
        text_column_12 text,
        text_column_13 text,
        text_column_14 text,
        text_column_15 text,
        text_column_16 text,
        text_column_17 text,
        text_column_2 text,
        text_column_3 text,
        text_column_4 text,
        text_column_5 text,
        text_column_6 text,
        text_column_7 text,
        text_column_8 text,
        text_column_9 text
    )
    WHERE raw_schema IN ('group001')
),
d3 AS (
INSERT INTO public.table3 (
    text_column_1,
    text_column_2,
    numeric_column_1,
    text_column_3,
    text_column_4
)
SELECT DISTINCT
    BTRIM(source_row.text_column_1),
    'SYNTHETIC/REFERENCE',
    NULL::numeric,
    LEFT(UPPER(BTRIM(source_row.text_column_2)), 1),
    RIGHT(UPPER(BTRIM(source_row.text_column_2)), 1)
FROM src AS source_row
WHERE BTRIM(source_row.text_column_1) <> ''
  AND UPPER(BTRIM(source_row.text_column_2)) ~ '^[A-Z]{2}$'
    RETURNING id_column_1, text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4
),
d4 AS (
INSERT INTO public.table4 (
    id_column_1,
    text_column_1,
    text_column_2
)
SELECT DISTINCT
    (
        (ASCII(LEFT(UPPER(BTRIM(source_row.text_column_3)), 1))
            - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(source_row.text_column_3)), 1))
        - ASCII('A')
        + 1
    )::smallint,
    'SYNTHETIC/GENERIC',
    UPPER(BTRIM(source_row.text_column_3))
FROM src AS source_row
WHERE UPPER(BTRIM(source_row.text_column_3)) ~ '^[A-Z]{2}$'
    RETURNING id_column_1, text_column_1, text_column_2
),
d1 AS (
INSERT INTO public.table1 (
    id_column_1,
    id_column_2,
    text_column_1,
    datetime_column_1,
    text_column_2,
    integer_column_1,
    integer_column_2,
    integer_column_3,
    text_column_3,
    id_column_3,
    id_column_4,
    id_column_5,
    integer_column_4,
    integer_column_5,
    id_column_6,
    integer_column_6,
    integer_column_7
)
SELECT
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    NULLIF(BTRIM(source_row.id_column_1), '')::integer,
    NULL::character varying,
    NULLIF(BTRIM(source_row.datetime_column_1), '')::timestamptz
        AT TIME ZONE 'America/Sao_Paulo',
    NULL::character varying,
    GREATEST(
        NULLIF(BTRIM(source_row.integer_column_2), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_3), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_4), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_5), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_6), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_7), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_8), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_9), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_10), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_11), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_12), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_13), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_14), '')::smallint,
        NULLIF(BTRIM(source_row.integer_column_15), '')::smallint
    ),
    NULL::smallint,
    CASE
        WHEN NULLIF(BTRIM(source_row.numeric_column_2), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(source_row.numeric_column_2), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END,
    NULL::character varying,
    source_row.raw_id,
    dimension_row.id_column_1,
    NULL::bigint,
    NULL::integer,
    NULL::integer,
    NULL::integer,
    NULL::integer,
    CASE
        WHEN NULLIF(BTRIM(source_row.numeric_column_1), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(source_row.numeric_column_1), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END
FROM src AS source_row
JOIN d3 AS dimension_row
  ON dimension_row.text_column_1 = BTRIM(source_row.text_column_1)
 AND dimension_row.text_column_2 = 'SYNTHETIC/REFERENCE'
 AND dimension_row.numeric_column_1 IS NULL
 AND dimension_row.text_column_3 = LEFT(
        UPPER(BTRIM(source_row.text_column_2)),
        1
    )
 AND dimension_row.text_column_4 = RIGHT(
        UPPER(BTRIM(source_row.text_column_2)),
        1
    )
    RETURNING id_column_1, id_column_3
),
d5 AS (
INSERT INTO public.table5 (
    numeric_column_1,
    numeric_column_2,
    integer_column_1,
    integer_column_2,
    id_column_2,
    id_column_3
)
SELECT
    ROUND(
        NULLIF(BTRIM(source_row.integer_column_1), '')::numeric,
        1
    ),
    NULL::numeric,
    NULL::integer,
    NULL::integer,
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    NULL::bigint
FROM src AS source_row
WHERE NULLIF(BTRIM(source_row.integer_column_1), '')::numeric > 0
    RETURNING id_column_1
),
d6 AS (
INSERT INTO public.table6 (
    id_column_2,
    id_column_3
)
SELECT
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    reference_row.id_column_1
FROM src AS source_row
JOIN d4 AS reference_row
  ON reference_row.text_column_1 = 'SYNTHETIC/GENERIC'
 AND reference_row.text_column_2 = UPPER(
        BTRIM(source_row.text_column_3)
    )
    RETURNING id_column_1
),
d2 AS (
INSERT INTO public.table2 (
    id_column_2,
    integer_column_1,
    integer_column_2,
    text_column_1,
    integer_column_3,
    integer_column_4,
    integer_column_5,
    integer_column_6
)
SELECT
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    position_data.position_number,
    ROUND(
        NULLIF(BTRIM(position_data.weight_text), '')::numeric * 1000
    )::integer,
    UPPER(BTRIM(position_data.type_text)),
    NULL::integer,
    NULL::integer,
    NULL::integer,
    CASE
        WHEN NULLIF(BTRIM(position_data.gap_text), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(position_data.gap_text), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END
FROM src AS source_row
CROSS JOIN LATERAL (
    VALUES
        (1::smallint, source_row.integer_column_2, source_row.text_column_4, source_row.numeric_column_3, source_row.numeric_column_4),
        (2::smallint, source_row.integer_column_3, source_row.text_column_5, source_row.numeric_column_5, source_row.numeric_column_6),
        (3::smallint, source_row.integer_column_4, source_row.text_column_6, source_row.numeric_column_7, source_row.numeric_column_8),
        (4::smallint, source_row.integer_column_5, source_row.text_column_7, source_row.numeric_column_9, source_row.numeric_column_10),
        (5::smallint, source_row.integer_column_6, source_row.text_column_8, source_row.numeric_column_11, source_row.numeric_column_12),
        (6::smallint, source_row.integer_column_7, source_row.text_column_9, source_row.numeric_column_13, source_row.numeric_column_14),
        (7::smallint, source_row.integer_column_8, source_row.text_column_10, source_row.numeric_column_15, source_row.numeric_column_16),
        (8::smallint, source_row.integer_column_9, source_row.text_column_11, source_row.numeric_column_17, source_row.numeric_column_18),
        (9::smallint, source_row.integer_column_10, source_row.text_column_12, source_row.numeric_column_19, source_row.numeric_column_20),
        (10::smallint, source_row.integer_column_11, source_row.text_column_13, source_row.numeric_column_21, source_row.numeric_column_22),
        (11::smallint, source_row.integer_column_12, source_row.text_column_14, source_row.numeric_column_23, source_row.numeric_column_24),
        (12::smallint, source_row.integer_column_13, source_row.text_column_15, source_row.numeric_column_25, source_row.numeric_column_26),
        (13::smallint, source_row.integer_column_14, source_row.text_column_16, source_row.numeric_column_27, source_row.numeric_column_28),
        (14::smallint, source_row.integer_column_15, source_row.text_column_17, source_row.numeric_column_29, source_row.numeric_column_30)
) AS position_data(position_number, declared_number_text, type_text, weight_text, gap_text)
WHERE NULLIF(BTRIM(position_data.declared_number_text), '')::smallint
        = position_data.position_number
  AND NULLIF(BTRIM(position_data.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(position_data.type_text)) IN ('X', 'Y', 'Z')
    RETURNING id_column_1
)
SELECT
    (SELECT count(*) FROM d1) AS table1_rows,
    (SELECT count(*) FROM d5) AS table5_rows,
    (SELECT count(*) FROM d6) AS table6_rows,
    (SELECT count(*) FROM d2) AS table2_rows;
