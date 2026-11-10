INSERT INTO public.table6 (
    id_column_2,
    id_column_3
)
SELECT
    source_row.raw_id + COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint,
    reference_row.id_column_1
FROM {{source}} AS source_row
CROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(
  text_column_3 text
)
JOIN public.table4 AS reference_row
  ON reference_row.text_column_1 = 'SYNTHETIC/GENERIC'
 AND reference_row.text_column_2 = UPPER(
        BTRIM(v.text_column_3)
    );
