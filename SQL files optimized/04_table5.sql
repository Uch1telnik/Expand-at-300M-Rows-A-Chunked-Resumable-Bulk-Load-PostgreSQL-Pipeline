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
        NULLIF(BTRIM(v.integer_column_1), '')::numeric,
        1
    ),
    NULL::numeric,
    NULL::integer,
    NULL::integer,
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    NULL::bigint
FROM {{source}} AS source_row
CROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(
  integer_column_1 text
)
WHERE NULLIF(BTRIM(v.integer_column_1), '')::numeric > 0;
