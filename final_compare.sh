#!/bin/bash
# Final end-to-end semantic check: baseline snapshot vs optimized pipeline output.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
# Credentials come from the environment (PGPASSWORD / PGSSHPASSWORD) or ~/.pgpass.
export PGHOST="${PGHOST:-127.0.0.1}" PGPORT="${PGPORT:-5433}" PGUSER="${PGUSER:-challenge}"
PSQL="psql -h $PGHOST -p $PGPORT -U $PGUSER -d kaggle_challenge -X -qAt -v ON_ERROR_STOP=1"

echo "== baseline snapshot rebuild =="
$PSQL -f "$SCRIPT_DIR/reset.sql" >/dev/null
$PSQL -f "$SCRIPT_DIR/wrapped_debug.sql" >/dev/null
$PSQL <<'SQL'
DROP TABLE IF EXISTS base_t1, base_t2, base_t3, base_t4, base_t5, base_t6;
CREATE TABLE base_t3 AS
  SELECT text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4 FROM table3;
CREATE TABLE base_t1 AS
  SELECT id_column_2, text_column_1, datetime_column_1, text_column_2, integer_column_1,
         integer_column_2, integer_column_3, text_column_3, id_column_3 AS raw_id,
         (SELECT text_column_1 FROM table3 d WHERE d.id_column_1 = table1.id_column_4) AS dim_text,
         integer_column_4, integer_column_5, id_column_6, integer_column_6, integer_column_7
  FROM table1;
CREATE TABLE base_t5 AS
  SELECT numeric_column_1, numeric_column_2, integer_column_1, integer_column_2,
         (SELECT id_column_3 FROM table1 m WHERE m.id_column_1 = table5.id_column_2) AS raw_id,
         id_column_3
  FROM table5;
CREATE TABLE base_t6 AS
  SELECT (SELECT id_column_3 FROM table1 m WHERE m.id_column_1 = table6.id_column_2) AS raw_id,
         (SELECT text_column_2 FROM table4 r WHERE r.id_column_1 = table6.id_column_3) AS ref_text
  FROM table6;
CREATE TABLE base_t2 AS
  SELECT (SELECT id_column_3 FROM table1 m WHERE m.id_column_1 = table2.id_column_2) AS raw_id,
         integer_column_1, integer_column_2, text_column_1, integer_column_3,
         integer_column_4, integer_column_5, integer_column_6
  FROM table2;
SQL

echo "== optimized pipeline =="
$PSQL -f "$SCRIPT_DIR/reset.sql" >/dev/null
$PSQL -c 'DROP SCHEMA IF EXISTS pgdm_runtime CASCADE;' >/dev/null 2>&1 || true
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000 > /tmp/final_run3.log 2>&1
tail -16 /tmp/final_run3.log
$PSQL <<'SQL'
DROP TABLE IF EXISTS opt_t1, opt_t2, opt_t3, opt_t4, opt_t5, opt_t6;
CREATE TABLE opt_t3 AS
  SELECT text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4 FROM table3;
CREATE TABLE opt_t1 AS
  SELECT id_column_2, text_column_1, datetime_column_1, text_column_2, integer_column_1,
         integer_column_2, integer_column_3, text_column_3, id_column_3 AS raw_id,
         (SELECT text_column_1 FROM table3 d WHERE d.id_column_1 = table1.id_column_4) AS dim_text,
         integer_column_4, integer_column_5, id_column_6, integer_column_6, integer_column_7
  FROM table1;
CREATE TABLE opt_t5 AS
  SELECT numeric_column_1, numeric_column_2, integer_column_1, integer_column_2,
         id_column_2 AS raw_id, id_column_3
  FROM table5;
CREATE TABLE opt_t6 AS
  SELECT id_column_2 AS raw_id,
         (SELECT text_column_2 FROM table4 r WHERE r.id_column_1 = table6.id_column_3) AS ref_text
  FROM table6;
CREATE TABLE opt_t2 AS
  SELECT id_column_2 AS raw_id, integer_column_1, integer_column_2, text_column_1,
         integer_column_3, integer_column_4, integer_column_5, integer_column_6
  FROM table2;
SQL

echo "== symmetric difference (must be 0) =="
for pair in "t1 base_t1 opt_t1" "t2 base_t2 opt_t2" "t3 base_t3 opt_t3" "t5 base_t5 opt_t5" "t6 base_t6 opt_t6"; do
  set -- $pair
  $PSQL -c "SELECT '$1', (SELECT count(*) FROM ((SELECT * FROM $2 EXCEPT ALL SELECT * FROM $3) UNION ALL (SELECT * FROM $3 EXCEPT ALL SELECT * FROM $2)) d);"
done
