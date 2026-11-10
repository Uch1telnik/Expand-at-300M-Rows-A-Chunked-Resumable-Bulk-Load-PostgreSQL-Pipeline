"""Bulk-load optimisation experiment: drop child indexes/FKs during load.

The expansion already holds SHARE ROW EXCLUSIVE on all destination tables, so
rebuilding indexes and re-validating foreign keys inside the same transaction
is safe: no reader can observe an intermediate state, and PostgreSQL validates
the FK data when the constraint is re-added (NOT VALID is never used).
"""
from pathlib import Path

idx_sql = Path("recreate_indexes.sql").read_text(encoding="utf-8")

body = Path("typed_staging.sql").read_text(encoding="utf-8")
# remove the leading SET lines; they are re-added by the harness
lines = [ln for ln in body.splitlines() if not ln.strip().upper().startswith("SET ")]
body = "\n".join(lines)

drop_sql = """
ALTER TABLE public.table1 DROP CONSTRAINT IF EXISTS table1_id_column_3_fkey,
    DROP CONSTRAINT IF EXISTS table1_id_column_4_fkey;
ALTER TABLE public.table2 DROP CONSTRAINT IF EXISTS table2_id_column_2_fkey;
ALTER TABLE public.table5 DROP CONSTRAINT IF EXISTS table5_id_column_2_fkey;
ALTER TABLE public.table6 DROP CONSTRAINT IF EXISTS table6_id_column_2_fkey,
    DROP CONSTRAINT IF EXISTS table6_id_column_3_fkey;
ALTER TABLE public.table1 DROP CONSTRAINT IF EXISTS table1_pkey,
    DROP CONSTRAINT IF EXISTS table1_id_column_3_key;
ALTER TABLE public.table2 DROP CONSTRAINT IF EXISTS table2_pkey,
    DROP CONSTRAINT IF EXISTS table2_id_column_2_integer_column_1_key;
ALTER TABLE public.table3 DROP CONSTRAINT IF EXISTS table3_pkey;
ALTER TABLE public.table4 DROP CONSTRAINT IF EXISTS table4_pkey;
ALTER TABLE public.table5 DROP CONSTRAINT IF EXISTS table5_pkey;
DROP INDEX IF EXISTS public.table5_id_column_2_when_id_column_3_null_key;
DROP INDEX IF EXISTS public.table5_id_column_3_not_null_key;
ALTER TABLE public.table6 DROP CONSTRAINT IF EXISTS table6_pkey,
    DROP CONSTRAINT IF EXISTS table6_id_column_2_id_column_3_key;
""".strip()

Path("bulkload.sql").write_text(
    drop_sql + "\n\n" + body + "\n\n" + idx_sql + "\n", encoding="utf-8"
)
print("wrote bulkload.sql")
