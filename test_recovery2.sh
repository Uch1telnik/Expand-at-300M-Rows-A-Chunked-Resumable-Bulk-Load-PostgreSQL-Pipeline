#!/bin/bash
# Interrupt after several committed chunks, then resume and prove integrity.
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
# Credentials come from the environment (PGPASSWORD) or ~/.pgpass.
export PGHOST="${PGHOST:-127.0.0.1}" PGPORT="${PGPORT:-5433}" PGUSER="${PGUSER:-challenge}"
PSQL="psql -h $PGHOST -p $PGPORT -U $PGUSER -d kaggle_challenge -X -qAt -v ON_ERROR_STOP=1"

$PSQL -c 'DROP SCHEMA IF EXISTS pgdm_runtime CASCADE;' >/dev/null 2>&1
$PSQL -f "$SCRIPT_DIR/reset.sql" >/dev/null

echo "== start expansion, kill client after 20s (some chunks committed) =="
setsid python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 100000 >/tmp/crash2.log 2>&1 &
PID=$!
sleep 20
pkill -9 -f optimized_pipeline.py 2>/dev/null
wait $PID 2>/dev/null
echo "committed chunks:"
$PSQL -c "SELECT chunk_index FROM pgdm_runtime.expansion_chunks ORDER BY 1;"
echo "table1 rows:"
$PSQL -c "SELECT count(*) FROM public.table1;"
echo "job:"
$PSQL -c "SELECT status, index_state FROM pgdm_runtime.expansion_jobs;"
echo "indexes present:"
$PSQL -c "SELECT count(*) FROM pg_constraint WHERE conrelid='public.table1'::regclass AND conname='table1_pkey';"

echo "== resume =="
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 100000 --resume >/tmp/resume2.log 2>&1
tail -25 /tmp/resume2.log

echo "== duplicate / gap checks =="
$PSQL -c "SELECT 'duplicate_raw_id', count(*) FROM (SELECT id_column_3 FROM public.table1 GROUP BY 1 HAVING count(*)>1) d;"
$PSQL -c "SELECT 'duplicate_table2_key', count(*) FROM (SELECT id_column_2, integer_column_1 FROM public.table2 GROUP BY 1,2 HAVING count(*)>1) d;"
$PSQL -c "SELECT 'missing_raw', count(*) FROM public.raw_data r WHERE r.raw_schema='group001' AND NOT EXISTS (SELECT 1 FROM public.table1 t WHERE t.id_column_3=r.raw_id);"
$PSQL -c "SELECT 'fk_violations', count(*) FROM public.table2 c WHERE NOT EXISTS (SELECT 1 FROM public.table1 p WHERE p.id_column_1=c.id_column_2);"
