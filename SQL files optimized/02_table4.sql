INSERT INTO public.table4 (
    id_column_1,
    text_column_1,
    text_column_2
)
SELECT DISTINCT
    (
        (ASCII(LEFT(UPPER(BTRIM(v.text_column_3)), 1))
            - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(v.text_column_3)), 1))
        - ASCII('A')
        + 1
    )::smallint,
    'SYNTHETIC/GENERIC',
    UPPER(BTRIM(v.text_column_3))
FROM {{source}} AS source_row
CROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(
  text_column_3 text
)
WHERE UPPER(BTRIM(v.text_column_3)) ~ '^[A-Z]{2}$';
