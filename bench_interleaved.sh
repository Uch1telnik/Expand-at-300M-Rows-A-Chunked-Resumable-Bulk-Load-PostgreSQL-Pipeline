#!/bin/bash
# Interleaved baseline vs optimized; all outputs persisted on the C: mount.
set -u
cd /mnt/c/Users/golub/Downloads/tsk/repo
mkdir -p results
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=challenge PGPASSWORD=challengepass
PSQL="psql -h 127.0.0.1 -p 5433 -U challenge -d kaggle_challenge -X -qAt -v ON_ERROR_STOP=1"
reset_dest() { $PSQL -f /mnt/c/Users/golub/Downloads/tsk/reset.sql >/dev/null 2>&1; }
drop_runtime() { $PSQL -c 'DROP SCHEMA IF EXISTS pgdm_runtime CASCADE;' >/dev/null 2>&1 || true; }
warm() { $PSQL -c "SELECT count(*) FROM (SELECT raw FROM public.raw_data) s;" >/dev/null; }

for ROUND in 1 2; do
  echo "===== ROUND $ROUND =====" | tee -a results/bench.log
  reset_dest; drop_runtime; warm
  /usr/bin/time -f "baseline wall=%es rss=%MKB" \
      python3 run_expansion_linux.py kaggle_challenge "SQL files" "base_r${ROUND}" \
      > "results/base_r${ROUND}.out" 2> "results/base_r${ROUND}.time"
  grep 'MEASURED PROCESSING TOTAL' "results/base_r${ROUND}.out" | tee -a results/bench.log
  cat "results/base_r${ROUND}.time" | tee -a results/bench.log

  reset_dest; drop_runtime
  /usr/bin/time -f "optimized wall=%es rss=%MKB" \
      python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000 \
      > "results/opt_r${ROUND}.out" 2> "results/opt_r${ROUND}.time"
  grep -E '"chunk_seconds"|"index_rebuild_seconds"|"table2_rows"' "results/opt_r${ROUND}.out" | tee -a results/bench.log
  cat "results/opt_r${ROUND}.time" | tee -a results/bench.log
done
