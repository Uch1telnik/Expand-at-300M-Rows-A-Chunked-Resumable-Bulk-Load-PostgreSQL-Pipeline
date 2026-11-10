"""Build the fused single-pass expansion with one jsonb_to_record parse per row."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "SQL files"

FIELD = re.compile(r"source_row\.raw\s*->\s*'values'\s*->>\s*'([a-z_0-9]+)'")
OFFSET = "COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint"

# union of every field referenced by the six recipes
USED = sorted(
    {
        field
        for path in SRC.glob("*.sql")
        for field in FIELD.findall(path.read_text(encoding="utf-8"))
    }
)


def transform(text):
    text = FIELD.sub(lambda m: f"source_row.{m.group(1)}", text)
    text = text.replace("FROM {{source}} AS source_row", "FROM src AS source_row")
    text = text.replace("JOIN public.table3 AS dimension_row", "JOIN d3 AS dimension_row")
    text = text.replace("JOIN public.table4 AS reference_row", "JOIN d4 AS reference_row")
    text = re.sub(
        r"\nJOIN public\.table1 AS main_row\n\s+ON main_row\.id_column_3 = source_row\.raw_id",
        "",
        text,
    )
    text = text.replace("main_row.id_column_1", f"source_row.raw_id + {OFFSET}")
    return text.strip().rstrip(";")


def recipe(name):
    return (SRC / name).read_text(encoding="utf-8")


t1 = recipe("03_table1.sql")
t1 = t1.replace(
    "INSERT INTO public.table1 (\n    id_column_2,",
    "INSERT INTO public.table1 (\n    id_column_1,\n    id_column_2,",
    1,
)
t1 = t1.replace(
    "SELECT\n    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'id_column_1')",
    f"SELECT\n    source_row.raw_id + {OFFSET},\n    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'id_column_1')",
    1,
)

record_columns = ",\n        ".join(f"{name} text" for name in USED)

sql = f"""WITH src AS MATERIALIZED (
    SELECT raw_id, v.*
    FROM public.raw_data
    CROSS JOIN LATERAL jsonb_to_record(raw -> 'values') AS v(
        {record_columns}
    )
    WHERE raw_schema IN ('group001')
),
d3 AS (
{transform(recipe("01_table3.sql"))}
    RETURNING id_column_1, text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4
),
d4 AS (
{transform(recipe("02_table4.sql"))}
    RETURNING id_column_1, text_column_1, text_column_2
),
d1 AS (
{transform(t1)}
    RETURNING id_column_1, id_column_3
),
d5 AS (
{transform(recipe("04_table5.sql"))}
    RETURNING id_column_1
),
d6 AS (
{transform(recipe("05_table6.sql"))}
    RETURNING id_column_1
),
d2 AS (
{transform(recipe("06_table2.sql"))}
    RETURNING id_column_1
)
SELECT
    (SELECT count(*) FROM d1) AS table1_rows,
    (SELECT count(*) FROM d5) AS table5_rows,
    (SELECT count(*) FROM d6) AS table6_rows,
    (SELECT count(*) FROM d2) AS table2_rows;
"""
(ROOT / "fused_record.sql").write_text(sql, encoding="utf-8")
print("wrote fused_record.sql", len(sql), "bytes;", len(USED), "fields")
