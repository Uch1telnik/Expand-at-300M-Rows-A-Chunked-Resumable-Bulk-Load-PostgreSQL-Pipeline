INSERT INTO public.table3 (
    text_column_1,
    text_column_2,
    numeric_column_1,
    text_column_3,
    text_column_4
)
SELECT DISTINCT
    BTRIM(v.text_column_1),
    'SYNTHETIC/REFERENCE',
    NULL::numeric,
    LEFT(UPPER(BTRIM(v.text_column_2)), 1),
    RIGHT(UPPER(BTRIM(v.text_column_2)), 1)
FROM {{source}} AS source_row
CROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(
  text_column_1 text, text_column_2 text
)
WHERE BTRIM(v.text_column_1) <> ''
  AND UPPER(BTRIM(v.text_column_2)) ~ '^[A-Z]{2}$';
