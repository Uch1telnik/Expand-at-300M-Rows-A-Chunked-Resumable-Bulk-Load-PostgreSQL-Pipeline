"""Build the optimized six-recipe bundle used by the benchmark harness.

Optimizations (semantics preserving):
  * one jsonb_to_record() parse per source row instead of ~1 field extraction each
  * explicit deterministic table1.id_column_1 = raw_id + session offset, so the
    downstream tables can reference it directly instead of re-joining table1
  * table2/table5/table6 no longer join table1 at all
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "SQL files"
DST = ROOT / "SQL files optimized"
DST.mkdir(exist_ok=True)

FIELD_RE = re.compile(r"source_row\.raw\s*->\s*'values'\s*->>\s*'([a-z_0-9]+)'")
OFFSET = "COALESCE(current_setting('pgdm.table1_id_offset', true), '0')::bigint"


def field_record(used):
    return ", ".join(f"{name} text" for name in used)


def parse(path):
    text = path.read_text(encoding="utf-8")
    used = sorted(set(FIELD_RE.findall(text)))
    return text, used


def add_record_source(text, used):
    from_line = "FROM {{source}} AS source_row"
    injection = (
        from_line
        + "\nCROSS JOIN LATERAL jsonb_to_record(source_row.raw -> 'values') AS v(\n  "
        + field_record(used)
        + "\n)"
    )
    text = text.replace(from_line, injection, 1)
    return FIELD_RE.sub(lambda m: f"v.{m.group(1)}", text)


def write(name, text):
    (DST / name).write_text(text, encoding="utf-8")
    print("wrote", name)


# table3 / table4: straight field rewrite
for name in ("01_table3.sql", "02_table4.sql"):
    text, used = parse(SRC / name)
    write(name, add_record_source(text, used))

# table1: explicit deterministic id_column_1
text, used = parse(SRC / "03_table1.sql")
text = text.replace(
    "INSERT INTO public.table1 (\n    id_column_2,",
    "INSERT INTO public.table1 (\n    id_column_1,\n    id_column_2,",
    1,
)
text = text.replace(
    "SELECT\n    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'id_column_1')",
    f"SELECT\n    source_row.raw_id + {OFFSET},\n    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'id_column_1')",
    1,
)
write("03_table1.sql", add_record_source(text, used))

# table5: direct raw_id reference, no table1 join
text, used = parse(SRC / "04_table5.sql")
text = text.replace("main_row.id_column_1", f"source_row.raw_id + {OFFSET}")
text = re.sub(
    r"\nJOIN public\.table1 AS main_row\n\s+ON main_row\.id_column_3 = source_row\.raw_id",
    "",
    text,
)
write("04_table5.sql", add_record_source(text, used))

# table6: direct raw_id reference, keep table4 join
text, used = parse(SRC / "05_table6.sql")
text = text.replace("main_row.id_column_1", f"source_row.raw_id + {OFFSET}")
text = re.sub(
    r"FROM \{\{source\}\} AS source_row\nJOIN public\.table1 AS main_row\n\s+ON main_row\.id_column_3 = source_row\.raw_id\n",
    "FROM {{source}} AS source_row\n",
    text,
)
write("05_table6.sql", add_record_source(text, used))

# table2: direct raw_id reference, no table1 join
text, used = parse(SRC / "06_table2.sql")
text = text.replace("main_row.id_column_1", f"source_row.raw_id + {OFFSET}")
text = re.sub(
    r"\nJOIN public\.table1 AS main_row\n\s+ON main_row\.id_column_3 = source_row\.raw_id",
    "",
    text,
)
write("06_table2.sql", add_record_source(text, used))
