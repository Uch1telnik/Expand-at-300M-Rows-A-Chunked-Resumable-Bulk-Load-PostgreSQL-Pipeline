#!/bin/bash
# Compare optimized table4 against the original recipe evaluated directly.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
# Credentials come from the environment (PGPASSWORD) or ~/.pgpass.
export PGHOST="${PGHOST:-127.0.0.1}" PGPORT="${PGPORT:-5433}" PGUSER="${PGUSER:-challenge}"
PSQL="psql -h $PGHOST -p $PGPORT -U $PGUSER -d kaggle_challenge -X -qAt -v ON_ERROR_STOP=1"
SQL=$(sed 's/{{source}}/public.raw_data/g' "SQL files/02_table4.sql" | sed 's/^INSERT INTO public.table4/INSERT INTO tmp_t4/')
$PSQL -c 'DROP TABLE IF EXISTS tmp_t4; CREATE TABLE tmp_t4 (LIKE public.table4 INCLUDING ALL);'
echo "$SQL" | $PSQL
$PSQL -c "SELECT 't4', (SELECT count(*) FROM ((SELECT * FROM tmp_t4 EXCEPT ALL SELECT * FROM table4) UNION ALL (SELECT * FROM table4 EXCEPT ALL SELECT * FROM tmp_t4)) d);"
$PSQL -c 'DROP TABLE tmp_t4;'
