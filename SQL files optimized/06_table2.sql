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
FROM {{source}} AS source_row
CROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(
  integer_column_10 text, integer_column_11 text, integer_column_12 text, integer_column_13 text, integer_column_14 text, integer_column_15 text, integer_column_2 text, integer_column_3 text, integer_column_4 text, integer_column_5 text, integer_column_6 text, integer_column_7 text, integer_column_8 text, integer_column_9 text, numeric_column_10 text, numeric_column_11 text, numeric_column_12 text, numeric_column_13 text, numeric_column_14 text, numeric_column_15 text, numeric_column_16 text, numeric_column_17 text, numeric_column_18 text, numeric_column_19 text, numeric_column_20 text, numeric_column_21 text, numeric_column_22 text, numeric_column_23 text, numeric_column_24 text, numeric_column_25 text, numeric_column_26 text, numeric_column_27 text, numeric_column_28 text, numeric_column_29 text, numeric_column_3 text, numeric_column_30 text, numeric_column_4 text, numeric_column_5 text, numeric_column_6 text, numeric_column_7 text, numeric_column_8 text, numeric_column_9 text, text_column_10 text, text_column_11 text, text_column_12 text, text_column_13 text, text_column_14 text, text_column_15 text, text_column_16 text, text_column_17 text, text_column_4 text, text_column_5 text, text_column_6 text, text_column_7 text, text_column_8 text, text_column_9 text
)
CROSS JOIN LATERAL (
    VALUES
        (1::smallint, v.integer_column_2, v.text_column_4, v.numeric_column_3, v.numeric_column_4),
        (2::smallint, v.integer_column_3, v.text_column_5, v.numeric_column_5, v.numeric_column_6),
        (3::smallint, v.integer_column_4, v.text_column_6, v.numeric_column_7, v.numeric_column_8),
        (4::smallint, v.integer_column_5, v.text_column_7, v.numeric_column_9, v.numeric_column_10),
        (5::smallint, v.integer_column_6, v.text_column_8, v.numeric_column_11, v.numeric_column_12),
        (6::smallint, v.integer_column_7, v.text_column_9, v.numeric_column_13, v.numeric_column_14),
        (7::smallint, v.integer_column_8, v.text_column_10, v.numeric_column_15, v.numeric_column_16),
        (8::smallint, v.integer_column_9, v.text_column_11, v.numeric_column_17, v.numeric_column_18),
        (9::smallint, v.integer_column_10, v.text_column_12, v.numeric_column_19, v.numeric_column_20),
        (10::smallint, v.integer_column_11, v.text_column_13, v.numeric_column_21, v.numeric_column_22),
        (11::smallint, v.integer_column_12, v.text_column_14, v.numeric_column_23, v.numeric_column_24),
        (12::smallint, v.integer_column_13, v.text_column_15, v.numeric_column_25, v.numeric_column_26),
        (13::smallint, v.integer_column_14, v.text_column_16, v.numeric_column_27, v.numeric_column_28),
        (14::smallint, v.integer_column_15, v.text_column_17, v.numeric_column_29, v.numeric_column_30)
) AS position_data(position_number, declared_number_text, type_text, weight_text, gap_text)
WHERE NULLIF(BTRIM(position_data.declared_number_text), '')::smallint
        = position_data.position_number
  AND NULLIF(BTRIM(position_data.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(position_data.type_text)) IN ('X', 'Y', 'Z');
