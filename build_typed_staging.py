"""Typed single-pass staging benchmark (dev experiment).

One scan of raw_data converts each JSONB string field to its final SQL type
once, in a narrow UNLOGGED staging table.  All six destinations are then built
from that staging table with plain sequential scans, so no wide row is spilled
to temp files and no field is converted more than once.  The staging table is
dropped at the end of the transaction.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "typed_staging.sql"

INT_COLS = ", ".join(f"integer_column_{i} text" for i in range(1, 16))
TEXT_COLS = ", ".join(f"text_column_{i} text" for i in range(4, 18))
NUM_COLS = ", ".join(f"numeric_column_{i} text" for i in range(1, 31))

T1_INT = ",\n            ".join(
    f"NULLIF(BTRIM(integer_column_{i}), '')::smallint" for i in range(2, 16)
)

SQL = f"""SET client_min_messages = warning;
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
    {", ".join(f"int_{i} text" for i in range(1, 16))},
    {", ".join(f"txt_{i} text" for i in range(4, 18))},
    {", ".join(f"num_{i} text" for i in range(3, 31))}
);
TRUNCATE pgdm_expansion_stage;

INSERT INTO pgdm_expansion_stage
SELECT raw_id,
       NULLIF(BTRIM(id_column_1), '')::integer,
       NULLIF(BTRIM(datetime_column_1), '')::timestamptz AT TIME ZONE 'America/Sao_Paulo',
       text_column_1,
       text_column_2,
       text_column_3,
       GREATEST({T1_INT}),
       CASE WHEN NULLIF(BTRIM(numeric_column_1), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_1), '')::numeric * 1000)::integer END,
       CASE WHEN NULLIF(BTRIM(numeric_column_2), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_2), '')::numeric * 1000)::integer END,
       {", ".join(f"integer_column_{i}" for i in range(1, 16))},
       {", ".join(f"text_column_{i}" for i in range(4, 18))},
       {", ".join(f"numeric_column_{i}" for i in range(3, 31))}
FROM (
    SELECT raw_id, v.*
    FROM public.raw_data
    CROSS JOIN LATERAL jsonb_to_record(raw -> 'values') AS v(
        id_column_1 text, text_column_1 text, text_column_2 text, text_column_3 text,
        {TEXT_COLS},
        {INT_COLS},
        {NUM_COLS},
        datetime_column_1 text
    )
    WHERE raw_schema IN ('group001')
) AS src;
ANALYZE pgdm_expansion_stage;

INSERT INTO public.table3 (text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4)
SELECT DISTINCT BTRIM(t1), 'SYNTHETIC/REFERENCE', NULL::numeric,
       LEFT(UPPER(BTRIM(t2)), 1), RIGHT(UPPER(BTRIM(t2)), 1)
FROM pgdm_expansion_stage s
WHERE BTRIM(t1) <> '' AND UPPER(BTRIM(t2)) ~ '^[A-Z]{{2}}$';

INSERT INTO public.table4 (id_column_1, text_column_1, text_column_2)
SELECT DISTINCT
       ((ASCII(LEFT(UPPER(BTRIM(t3)), 1)) - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(t3)), 1)) - ASCII('A') + 1)::smallint,
       'SYNTHETIC/GENERIC', UPPER(BTRIM(t3))
FROM pgdm_expansion_stage s
WHERE UPPER(BTRIM(t3)) ~ '^[A-Z]{{2}}$';

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
""" + ",\n".join(
    f"    ({i}::smallint, s.int_{i + 1}, s.txt_{i + 3}, s.num_{i + 2}, s.num_{i + 3})"
    for i in range(1, 15)
) + """
) AS p(position_number, declared_number_text, type_text, weight_text, gap_text)
WHERE NULLIF(BTRIM(p.declared_number_text), '')::smallint = p.position_number
  AND NULLIF(BTRIM(p.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(p.type_text)) IN ('X', 'Y', 'Z');

SELECT setval(pg_get_serial_sequence('public.table1', 'id_column_1'),
              COALESCE((SELECT max(id_column_1) FROM public.table1), 1), true);
DROP TABLE pgdm_expansion_stage;
"""
OUT.write_text(SQL, encoding="utf-8")
print("wrote", OUT, len(SQL))
