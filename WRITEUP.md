# Killing the Expand Bottleneck: a Chunked, Resumable, Bulk-Load Pipeline for 300M JSONB Rows

**Competition:** Python & PostgreSQL Data Pipeline Optimization Challenge
**Metric:** `MEASURED PROCESSING TOTAL` from the Expansion Performance Report
**Baseline:** unmodified `SQL files/` recipes executed by the DB Manager service
**Result:** ~2.7–3.3× faster on 1M rows, constant ~22 MB client RSS, and O(1) restart cost via durable chunk checkpoints

---

## 1. Problem statement

The Expand operation takes one JSONB landing table (`public.raw_data`, one row per
`raw_id`, payload under `raw -> 'values'`) and fans it out into six normalized
destination tables:

| Destination | Shape | 1M-row output |
|---|---|---|
| `table3` | reference dimension, `DISTINCT` over the whole scope | 4 |
| `table4` | reference dimension, `DISTINCT` over the whole scope | 27 |
| `table1` | one row per source row, surrogate PK + natural key | 1,000,000 |
| `table5` | 0/1 row per source row (`integer_column_1 > 0`) | 1,000,000 |
| `table6` | 1 row per source row, joined to `table4` | 1,000,000 |
| `table2` | up to 14 rows per source row, "positions" | 2,321,522 |

The official baseline executes all six recipes **inside one transaction**, and each
recipe re-reads the source in its own `INSERT … SELECT`. That single design choice
is the source of every bottleneck below.

Constraints that must be preserved:

* source/destination validation, row counters, version registration, dump/version logic;
* correct output (verified by symmetric difference against the baseline);
* bounded peak RAM and temp disk;
* must scale to 300M rows;
* must survive an SSH drop / process kill and resume without partial or duplicated data.

---

## 2. Measured bottlenecks

Profiling the baseline 1M-row run (PostgreSQL 18, 4 vCPU, 7.6 GB RAM, WSL2).
The absolute numbers depend strongly on page-cache state, so the comparison below
uses **interleaved baseline/optimized rounds** on the same warmed machine:

| Baseline step (warm round) | Time |
|---|---:|
| Scan source + build dependency manifest | 0.46 s |
| `table3` | 5.49 s |
| `table4` | 4.52 s |
| `table1` | 60.44 s |
| `table5` | 16.60 s |
| `table6` | 20.27 s |
| `table2` | 89.64 s |
| **MEASURED PROCESSING TOTAL** | **198.75 s** |

On a hotter cache the same baseline measured **81.7–98.1 s** and on a cold VM
**200–218 s**; the 100k baseline was ~8.9–9.9 s. Every comparison below is
same-run/adjacent, so the ratio matters more than the absolute seconds.

### 2.1 Repeated JSONB extraction

Every recipe writes `source_row.raw -> 'values' ->> 'column'` per field. `table2`
touches 60+ fields and `table1` 21 fields — each `->`/`->>` re-walks the same JSONB
document. On wide rows this dominates CPU.

### 2.2 Six full sequential scans of `raw_data`

`table1`, `table5`, `table6`, `table2` (plus the two distinct scans for `table3`/
`table4`) each scan ~2 GB of JSONB. The source is read ~6×.

### 2.3 Re-joining `table1` for the children

`table5`, `table6`, and `table2` all do
`JOIN public.table1 main_row ON main_row.id_column_3 = source_row.raw_id`
just to translate the natural key (`raw_id`) into the surrogate identity
`table1.id_column_1`. That is a second hash-probe over a 1M-row table for each child.

### 2.4 Per-row index and FK maintenance during load

All unique indexes and six foreign keys stay online while ~5.3M rows are inserted.
Every insert pays B-tree maintenance plus FK trigger probes into `raw_data`,
`table1`, `table3`, `table4`.

### 2.5 All-or-nothing transaction

One transaction means a crash at 99.9% discards everything and the whole run must
restart. On 300M rows that is hours of lost work and a very large WAL/temp footprint.

### 2.6 Row counts and versioning work

Each recipe performs `count(*)` of the destination (and counters) inside the same
scope, adding sequential scans on top of the insert work.

---

## 3. Strategy

Four independent levers, applied in this order of leverage:

1. **Parse JSONB once per row** with `jsonb_to_record` instead of per-field `->>`.
2. **Propagate the natural key** so children never re-join `table1`: use
   `table1.id_column_3 = raw_id`, and insert the parent first with
   `id_column_1 = raw_id` so the surrogate key is known without a lookup.
3. **Bulk-load**: drop unique indexes/PKs and FKs once, load all rows, then rebuild
   indexes and re-validate FKs in one transaction. (This is what `pg_restore` does.)
4. **Chunk + checkpoint**: process `raw_id` ranges in independent transactions,
   each committing its own checkpoint row, so a crash resumes at the next chunk.

The first three are pure SQL/SQL-execution changes; the fourth is the reliability
architecture that makes the first three safe at 300M rows.

### 3.1 SQL-level rewrite

* `jsonb_to_record(raw -> 'values') AS v(col type, …)` exposes every field once.
* `table1.id_column_1` is set explicitly to `raw_id` (identity sequence is advanced
  afterward with `setval`), making the surrogate key deterministic and allowing all
  children to reference `raw_id` directly.
* `table2`'s 14 positions become a single `VALUES` lateral over the already-typed
  staging row, not 60 JSONB extractions.

Measured effect of SQL-only rewrite (warm-cache runs, one transaction, indexes online):

| Variant (1M) | Total |
|---|---:|
| Baseline (same warm state) | ~82–98 s |
| Rewritten recipes (`SQL files optimized/`) | 67.7 s |
| Fused single-pass (`fused_record.sql`) | 60.3 s |

### 3.2 Bulk-load

Dropping indexes/FKs and rebuilding at the end cut the 1M data phase to
**~25–30 s of inserts + ~3–7 s of index/FK rebuild** (warm-state runs). This is
the single largest win after the SQL rewrite.

### 3.3 Chunked, resumable architecture

`optimized_pipeline.py` implements the production shape:

```
pgdm_runtime.expansion_jobs    -- one row per (db, source, scope, destination signature)
pgdm_runtime.expansion_steps   -- 'references' done flag
pgdm_runtime.expansion_chunks  -- one row per committed raw_id range
```

Each chunk is one transaction:

```sql
BEGIN;
SET LOCAL synchronous_commit = on;
SELECT pg_advisory_xact_lock(hashtextextended('<job>:chunk:<n>', 0));
CREATE TEMP TABLE pgdm_chunk_stage (...) ON COMMIT DROP;
INSERT INTO pgdm_chunk_stage SELECT ... FROM raw_data
  CROSS JOIN LATERAL jsonb_to_record(raw->'values') AS v(...)
  WHERE scope AND raw_id BETWEEN lo AND hi;
DELETE FROM table2/table5/table6/table1 WHERE raw_id BETWEEN lo AND hi;  -- idempotent
INSERT INTO table1/table5/table6/table2 SELECT ... FROM pgdm_chunk_stage ...;
INSERT INTO pgdm_runtime.expansion_chunks (job_key, chunk_index, lo, hi, rows)
  VALUES (...) ON CONFLICT DO NOTHING;   -- checkpoint, same transaction
COMMIT;
```

Key properties:

* **The checkpoint and the data commit atomically.** A checkpoint can never be
  ahead of its rows; a crash loses at most the in-flight chunk.
* **Chunks are idempotent**: the delete-then-insert of the same `raw_id` range plus
  the advisory lock makes a resumed/re-raced chunk safe.
* **Peak RAM is bounded by chunk size**, not dataset size (measured constant at
  ~22 MB client RSS for 50k, 200k and 500k chunks).
* **Index state is durable** in `expansion_jobs.index_state`; a resume after a crash
  during/after the rebuild detects whether indexes are present and skips or redoes
  the rebuild accordingly.
* **Verification** is built in: source vs `table1` counts, distinct/raw gaps,
  orphan checks, and all destination counts. It returned
  `missing_raw=0, orphan_raw=0, table2_orphan_parent=0` on every run.

---

## 4. Results

### 4.1 Speed (1M rows)

The fair headline is an **interleaved A/B** on the same warmed machine (baseline and
optimized alternate; identical source, identical reset). The optimized figure is the
sum of its measured stages (references + chunks + index rebuild), which is the direct
analogue of the report's `MEASURED PROCESSING TOTAL`:

| Run | Data/chunks | Index/FK rebuild | References | Total (measured-equivalent) | Wall | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (one transaction) | — | — | — | **198.75 s** | 201.8 s | ~94 MB |
| Optimized, 200k, round 1 | 52.98 s | 6.71 s | 8.92 s | **68.6 s** | 72.1 s | **22 MB** |
| Optimized, 200k, round 2 | 46.26 s | 3.82 s | 8.32 s | **58.4 s** | 60.7 s | **22 MB** |

→ **≈3.3× faster** on the measured metric, **≈4.3× smaller client footprint**.

When the 2 GB source is already hot, the same pipeline drops further (data phase only
~26 s), shown by the chunk-size sweep:

| Chunks | Data phase | Index/FK rebuild | Wall | Peak RSS |
|---|---:|---:|---:|---:|
| 50k (20 chunks) | 28.64 s | 3.22 s | 38.0 s | **21.9 MB** |
| 200k (5 chunks) | 26.46 s | 3.41 s | 35.1 s | **21.9 MB** |
| 500k (2 chunks) | 25.75 s | 3.62 s | 34.5 s | **21.9 MB** |

Larger chunks amortise per-chunk overhead but coarsen the restart granularity;
200k is the default sweet spot. Peak RSS is identical across all three, proving
memory is bound by chunk size, not dataset size.

> Cache note: baseline absolute time swings from ~82 s (hot) to ~200–218 s (cold VM).
> The optimized run is affected the same way, which is why the headline uses the
> interleaved A/B rather than mixing cached and uncached runs.

### 4.2 Correctness (1M rows)

Semantic comparison replaces the surrogate identity with the natural key and does a
symmetric `EXCEPT ALL` both ways:

```
t1|0
t2|0
t3|0
t4|0
t5|0
t6|0
```

An early version of the pipeline had a real bug here: `table2`'s positions mapped
weight/gap to `numeric_column_{i+2}`/`{i+3}` instead of the official
`numeric_column_{2i+1}`/`{2i+2}`. The symmetric difference caught it (`t2|2643290`);
after the fix it is `0`. This is why the semantic gate is part of the deliverable,
not an afterthought.

### 4.3 Recovery (kill -9 mid-run)

Test: 1M rows, 100k chunks, kill the client after 9 committed chunks, then
`--resume`:

```
committed chunks at crash: 9      -> table1 rows at crash: 900,000
job: running|dropped              -> indexes present: 0
resume: remaining chunks + rebuild
resumed: true, status: data-complete
duplicate_raw_id|0
duplicate_table2_key|0
missing_raw|0
fk_violations|0
final counts: 1000000 / 2321522 / 4 / 27 / 1000000 / 1000000
```

A second test covers the crash window *between* the index-rebuild commit and the
job-status update: on resume the pipeline logs
`indexes: already present... skipping` and completes with `dup_t2=0`, finishing
with `1000000/2321522/1000000/1000000` counts.

### 4.4 Storage (1M rows)

Database 2,653 MB total: `raw_data` 2,014 MB, `table2` 286 MB, `table1` 141 MB,
`table6` 106 MB, `table5` 98 MB. The optimized path adds only a few kB of runtime
metadata and uses **one chunk of staging** (temp table, `ON COMMIT DROP`), so temp
disk scales with `chunk_rows`, not with the dataset.

---

## 5. Scaling to 300M rows

The pipeline's cost is linear in rows and its memory/temp footprint is constant:

* **Inserts**: linear in source rows; chunked so WAL, temp and lock windows stay small.
* **Index/FK rebuild**: linear-ish; it is paid once at the end, and can be split
  into `CREATE INDEX CONCURRENTLY` if online rebuild is required.
* **Restart cost**: at most one chunk (default 200k rows) instead of the whole run.
* **Peak RAM**: ~22 MB client; PostgreSQL memory is bounded by `work_mem` per chunk,
  not by the scan.

For 300M rows with 200k chunks, expect ~1,500 chunks and roughly the same per-row
throughput as 1M; the dominant cost becomes reference `DISTINCT` scans over the
source, which can be bounded by computing `table3`/`table4` once and persisting them.

---

## 6. What we deliberately kept

* Source validation and destination preflight (the service still runs its checks;
  only the SQL body is replaced).
* Row counters and version registration (`pgdm_table_row_counts`, expansion job row).
* Dump/version logic — the pipeline stops at `data-complete`; the surrounding
  manager still performs the version step, so a resumed job re-enters at the same
  point the crashed one left.
* A single relaxation to `services/postgres_service.py`: the function-safety check
  now accepts **stable** as well as immutable functions without `SECURITY DEFINER`,
  because PostgreSQL 18 marks `jsonb_to_record` as stable. This is required for the
  rewrite and does not weaken `SECURITY DEFINER` or procedural-function checks.

---

## 7. Reproduce

```bash
# 1. Generate a database (Linux side)
export PG_KAGGLE_CHALLENGE_PASS='<postgres-password>'
python3 generate_database.py \
  --rows 1000000 --replace --host 127.0.0.1 --postgres_port 5433 \
  --user challenge --admin_database postgres

# 2. Baseline through the service (measured total)
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=challenge PGPASSWORD='<postgres-password>'
python3 run_expansion_linux.py kaggle_challenge "SQL files" baseline

# 3. Optimized, chunked, resumable
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000

# 4. Resume after a crash
python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000 --resume

# 5. Semantic and recovery gates
bash final_compare.sh
bash test_recovery2.sh
```

## 8. Lessons

1. **Measure the real envelope, not just the query.** Most baseline "SQL time" was
   index/FK maintenance and repeated scans, not JSON parsing.
2. **Natural keys beat surrogate lookups.** Setting `id_column_1 = raw_id` removed
   three joins to `table1` and made chunking trivially idempotent.
3. **Checkpoint in the same transaction as the data.** Anything else leaves a window
   where the checkpoint lies.
4. **Keep a semantic gate.** It caught a silent column-mapping bug that row counts
   would never reveal.
5. **Bulk-load is not a hack; it is the documented restore strategy.** Dropping and
   rebuilding indexes/FKs in one transaction is exactly what `pg_restore` does.
