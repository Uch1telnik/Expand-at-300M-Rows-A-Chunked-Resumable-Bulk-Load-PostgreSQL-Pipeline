#!/bin/bash
# Edge case: all chunks done + indexes present, but job row still 'running'.
set -u
cd /mnt/c/Users/golub/Downloads/tsk/repo
mkdir -p results
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=challenge PGPASSWORD=challengepass
PSQL="psql -h 127.0.0.1 -p 5433 -U challenge -d kaggle_challenge -X -qAt -v ON_ERROR_STOP=1"
$PSQL -f /mnt/c/Users/golub/Downloads/tsk/reset.sql >/dev/null 2>&1
$PSQL -c 'DROP SCHEMA IF EXISTS pgdm_runtime CASCADE;' >/dev/null 2>&1 || true
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 100000 > results/edge_first.log 2>&1
# Simulate crash window: data + indexes committed, but job status not updated.
$PSQL -c "UPDATE pgdm_runtime.expansion_jobs SET status='running', index_state='dropping';" >/dev/null
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 100000 --resume > results/edge_resume.log 2>&1
echo "resume_exit=$?"
grep -E 'indexes:|data phase:|"status"|"resumed"' results/edge_resume.log | tee results/edge.log
$PSQL -c "SELECT 't1', count(*) FROM public.table1;" | tee -a results/edge.log
$PSQL -c "SELECT 'dup_t2', count(*) FROM (SELECT id_column_2,integer_column_1 FROM public.table2 GROUP BY 1,2 HAVING count(*)>1) d;" | tee -a results/edge.log
$PSQL -c "SELECT 'counts', (SELECT count(*) FROM table1)||'/'||(SELECT count(*) FROM table2)||'/'||(SELECT count(*) FROM table5)||'/'||(SELECT count(*) FROM table6);" | tee -a results/edge.log
