# Solution artifacts — Expand pipeline optimization

This folder contains the reference optimized Expand implementation plus every
benchmark/validation harness used to produce the numbers in [WRITEUP.md](./WRITEUP.md).

## Primary deliverable

| File | Purpose |
|---|---|
| `optimized_pipeline.py` | Chunked, resumable, bulk-load Expand pipeline (drop-in replacement for the Expand data phase). |
| `WRITEUP.md` | Kaggle writeup: bottlenecks, strategy, architecture, metrics, recovery. |
| `services/postgres_service.py` | One-line relaxation: the function-safety gate now accepts `stable` functions (required by `jsonb_to_record` in PG18). |

## SQL variants (research, same semantics)

| File | Description |
|---|---|
| `SQL files/` | Official baseline recipes (unchanged). |
| `SQL files optimized/` | Recipes rewritten with one `jsonb_to_record` per row + natural-key propagation. |
| `fused_record.sql` | Fused single-pass variant (all destinations in one statement set). |
| `typed_staging.sql` | Typed staging variant. |
| `bulkload.sql`, `recreate_indexes.sql` | Bulk-load without indexes, then rebuild. |

## Validation / benchmarking harnesses

| File | Purpose |
|---|---|
| `run_expansion_linux.py` | Runs a recipe folder through the real service layer and prints `MEASURED PROCESSING TOTAL`. |
| `benchmark_variant.py` | Benchmarks an arbitrary SQL file inside the timing envelope. |
| `final_compare.sh` | Baseline-vs-optimized symmetric `EXCEPT ALL` semantic gate (must be all zero). |
| `check_table4.sh` | `table4` equality against the original recipe. |
| `test_recovery2.sh` | `kill -9` mid-run, then `--resume`, plus duplicate/gap/FK checks. |
| `test_edge.sh` | Crash between index-rebuild commit and status update (idempotent resume). |
| `bench_interleaved.sh` | Interleaved baseline vs optimized rounds (fair, same cache state). |
| `results/` | Raw logs for the scaling, recovery, edge-case and interleaved benchmarks. |

## Builders

`build_optimized_recipes.py`, `build_fused_record.py`, `build_typed_staging.py`,
`build_bulkload.py`, `build_fused.py`, `split_typed.py`, `debug_timing.py`.

## Environment

* WSL2 Ubuntu, PostgreSQL 18 (`pg_ctlcluster 18 main start`, port **5433**), SSH on 22.
* DB `kaggle_challenge`, role `challenge` / `challengepass`.
* Generate data:
  ```bash
  PG_KAGGLE_CHALLENGE_PASS=challengepass python3 generate_database.py \
    --rows 1000000 --replace --host 127.0.0.1 --postgres_port 5433 \
    --user challenge --admin_database postgres
  ```
* Run optimized pipeline:
  ```bash
  PGHOST=127.0.0.1 PGPORT=5433 PGUSER=challenge PGPASSWORD=challengepass \
    python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000
  ```
* Resume after a crash: add `--resume`.
* `reset.sql` must precede a baseline rerun (destination tables must be empty).
