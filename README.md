# Expand at 300M Rows — a Chunked, Resumable, Bulk-Load PostgreSQL Pipeline

Optimization entry for the Kaggle **Python & PostgreSQL Data Pipeline Optimization
Challenge**. The task is to expand one JSONB landing table (`public.raw_data`) into
six normalized tables, measured by `MEASURED PROCESSING TOTAL` from the Expansion
Performance Report.

| | Baseline | Optimized |
|---|---:|---:|
| 1M rows, measured total | 198.8 s | ~58–69 s (**≈3.3× faster**) |
| Peak client RSS | ~94 MB | **~22 MB** (~4.3× less) |
| Restart after crash | whole run | **one chunk (O(1))** |
| Semantic difference | — | **0** on all six tables |

Read the full writeup: **[WRITEUP.md](./WRITEUP.md)**

## What is optimized

1. **One JSONB parse per row** — `jsonb_to_record(raw -> 'values')` replaces dozens
   of `->>` extractions per recipe.
2. **Natural-key propagation** — `table1.id_column_1 = raw_id`, so `table2`, `table5`
   and `table6` never re-join `table1`.
3. **Bulk load** — unique indexes/PKs and FKs are dropped once, rows are loaded, then
   everything is rebuilt and re-validated in one transaction (the `pg_restore` strategy).
4. **Chunk + checkpoint** — `raw_id` ranges are processed in independent transactions;
   each commits its own checkpoint row *in the same transaction as its data*, so a
   crash can never leave a partially applied chunk or a checkpoint ahead of the rows.

## Repository layout

```
optimized_pipeline.py          # main deliverable: chunked, resumable, bulk-load Expand
generate_database.py           # deterministic dataset generator (1M rows, stdlib + psql)
SQL files optimized/           # six recipes rewritten around jsonb_to_record
SQL files/                     # original baseline recipes
services/postgres_service.py   # only source change: function-safety gate allows `stable`
config.py, utils.py            # imported by the service layer
fused_record.sql               # research variant: fused single pass
typed_staging.sql              # research variant: typed staging
bulkload.sql, recreate_indexes.sql
reset.sql                      # truncate destinations before a baseline run
wrapped_debug.sql              # baseline snapshot used by final_compare.sh
build_*.py                     # generators for the SQL variants above
run_expansion_linux.py         # runs a recipe folder through the real service layer
benchmark_variant.py           # benchmarks an arbitrary SQL file in the timing envelope
final_compare.sh               # baseline vs optimized symmetric EXCEPT ALL gate
check_table4.sh                # table4 equality check
test_recovery2.sh              # kill -9 mid-run, then --resume, integrity checks
test_edge.sh                   # crash between index rebuild and status update
bench_interleaved.sh           # fair A/B on the same warmed machine
results/                       # raw logs used as evidence in the writeup
assets/                        # card (16:9 and 1:1) and gallery charts
```

Requirements: `pip install -r requirements.txt` (the pipeline itself only needs `psql`
and the Python standard library; the GUI service layer pulls the rest).

Credentials are never committed — copy `.env.example` to `.env` and fill it in, or export
`PGHOST/PGPORT/PGUSER/PGPASSWORD` (and `PGSSHUSER/PGSSHPASSWORD` for the SSH runners).

Supplementary docs: [SOLUTION.md](./SOLUTION.md), [KAGGLE_FIELDS.md](./KAGGLE_FIELDS.md).

## Reproduce

Prerequisites: PostgreSQL 18 (here on port 5433) reachable over SSH, plus `psql`.

```bash
# 0. Credentials come from the environment (never committed)
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=challenge PGPASSWORD='<postgres-password>'
export PGSSHUSER=root PGSSHPASSWORD='<ssh-password>'   # only for the SSH runners

# 1. Generate the deterministic dataset (1M rows)
export PG_KAGGLE_CHALLENGE_PASS="$PGPASSWORD"
python3 generate_database.py \
  --rows 1000000 --replace --host 127.0.0.1 --postgres_port 5433 \
  --user challenge --admin_database postgres

# 2. Baseline, measured through the real service layer
python3 run_expansion_linux.py kaggle_challenge "SQL files" baseline

# 3. Optimized pipeline
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000

# 4. Resume after a crash
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000 --resume

# 5. Verification gates
bash final_compare.sh
bash test_recovery2.sh
```

The baseline requires empty destination tables first
(`TRUNCATE table2, table5, table6, table1, table3, table4 RESTART IDENTITY CASCADE;`).

## Correctness evidence

`final_compare.sh` keys both runs by the natural key and does a symmetric
`EXCEPT ALL`; all six comparisons are `0`:

```
t1|0  t2|0  t3|0  t4|0  t5|0  t6|0
```

Recovery evidence (`results/recovery.log`): after `kill -9` at 9 committed chunks,
`--resume` finished with `duplicate_raw_id=0`, `duplicate_table2_key=0`,
`missing_raw=0`, `fk_violations=0` and final counts
`1000000 / 2321522 / 4 / 27 / 1000000 / 1000000`.

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
