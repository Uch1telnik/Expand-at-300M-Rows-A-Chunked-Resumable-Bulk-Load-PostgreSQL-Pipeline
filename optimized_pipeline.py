"""Chunked, resumable, single-scan expansion pipeline for the challenge.

Drop-in replacement for the Expand data phase.  It keeps the original
guarantees (source validation, destination validation, version registration,
dump/version logic) and adds:

  * one JSONB parse per source row (jsonb_to_record) instead of one per field;
  * typed temporary staging per chunk, so every field is converted exactly once;
  * natural-key propagation (table1.id_column_1 = raw_id), so table2/5/6 never
    re-join table1 and the raw_data / reference tables are never re-read;
  * raw_id-range chunking with a durable checkpoint row written in the *same
    transaction* as the destination rows, so a crash can never leave a chunk
    half-applied or a checkpoint ahead of data;
  * automatic resume: completed chunks are skipped, uncommitted ones are gone;
  * optional post-run verification (counts + foreign-key integrity);
  * peak memory bounded by chunk size, not dataset size (scales to 300M rows).

Usage (reference implementation, Linux/psql):
    python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000
    python3 optimized_pipeline.py --db kaggle_challenge --chunk-rows 200000 --resume
    python3 optimized_pipeline.py --db kaggle_challenge --verify

The SQL generation is transport-agnostic: pass any callable that executes a SQL
script against a database and returns stdout.  ``PsqlRunner`` is provided for
local psql; the same class can be wired to PostgresAdminService.run_remote_command
for the SSH path used by the desktop app.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_SCHEMA = "pgdm_runtime"
DESTINATIONS = ("table3", "table4", "table1", "table5", "table6", "table2")

# Columns of the typed staging table, in insert order.
STAGE_COLUMNS = (
    ["raw_id", "id1", "dt1", "t1", "t2", "t3", "max_int2", "num1", "num2"]
    + [f"int_{i}" for i in range(1, 16)]
    + [f"txt_{i}" for i in range(4, 18)]
    + [f"num_{i}" for i in range(3, 31)]
)

FIELD_TYPES = (
    ["id_column_1 text", "text_column_1 text", "text_column_2 text", "text_column_3 text"]
    + [f"text_column_{i} text" for i in range(4, 18)]
    + [f"integer_column_{i} text" for i in range(1, 16)]
    + [f"numeric_column_{i} text" for i in range(1, 31)]
    + ["datetime_column_1 text"]
)


def _column_list() -> str:
    return ",\n        ".join(FIELD_TYPES)


STAGE_DDL = f"""
CREATE TEMP TABLE pgdm_chunk_stage (
    raw_id bigint PRIMARY KEY,
    id1 integer,
    dt1 timestamp,
    t1 text, t2 text, t3 text,
    max_int2 smallint,
    num1 integer, num2 integer,
    {", ".join(f"int_{i} text" for i in range(1, 16))},
    {", ".join(f"txt_{i} text" for i in range(4, 18))},
    {", ".join(f"num_{i} text" for i in range(3, 31))}
) ON COMMIT DROP;
""".strip()

GREATEST_INT2 = ",\n            ".join(
    f"NULLIF(BTRIM(integer_column_{i}), '')::smallint" for i in range(2, 16)
)

STAGE_FILL = f"""
INSERT INTO pgdm_chunk_stage
SELECT raw_id,
       NULLIF(BTRIM(id_column_1), '')::integer,
       NULLIF(BTRIM(datetime_column_1), '')::timestamptz AT TIME ZONE 'America/Sao_Paulo',
       text_column_1, text_column_2, text_column_3,
       GREATEST({GREATEST_INT2}),
       CASE WHEN NULLIF(BTRIM(numeric_column_1), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_1), '')::numeric * 1000)::integer END,
       CASE WHEN NULLIF(BTRIM(numeric_column_2), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(numeric_column_2), '')::numeric * 1000)::integer END,
       {", ".join(f"integer_column_{i}" for i in range(1, 16))},
       {", ".join(f"text_column_{i}" for i in range(4, 18))},
       {", ".join(f"numeric_column_{i}" for i in range(3, 31))}
FROM (
    SELECT raw_id, v.*
    FROM public.__SOURCE__
    CROSS JOIN LATERAL jsonb_to_record(raw -> 'values') AS v(
        {_column_list()}
    )
    WHERE __SCOPE__
      AND raw_id BETWEEN :lo AND :hi
) AS src;
""".strip()

REFERENCE_SQL = """
-- Reference dimensions are tiny and derived from the whole source scope.
INSERT INTO public.table3 (text_column_1, text_column_2, numeric_column_1, text_column_3, text_column_4)
SELECT DISTINCT BTRIM(v.text_column_1), 'SYNTHETIC/REFERENCE', NULL::numeric,
       LEFT(UPPER(BTRIM(v.text_column_2)), 1), RIGHT(UPPER(BTRIM(v.text_column_2)), 1)
FROM public.__SOURCE__ s
CROSS JOIN LATERAL jsonb_to_record(s.raw -> 'values') AS v(text_column_1 text, text_column_2 text)
WHERE __SCOPE__ AND BTRIM(v.text_column_1) <> '' AND UPPER(BTRIM(v.text_column_2)) ~ '^[A-Z]{2}$';

INSERT INTO public.table4 (id_column_1, text_column_1, text_column_2)
SELECT DISTINCT
       ((ASCII(LEFT(UPPER(BTRIM(v.text_column_3)), 1)) - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(v.text_column_3)), 1)) - ASCII('A') + 1)::smallint,
       'SYNTHETIC/GENERIC', UPPER(BTRIM(v.text_column_3))
FROM public.__SOURCE__ s
CROSS JOIN LATERAL jsonb_to_record(s.raw -> 'values') AS v(text_column_3 text)
WHERE __SCOPE__ AND UPPER(BTRIM(v.text_column_3)) ~ '^[A-Z]{2}$';
""".strip()

CHUNK_MAIN = """
-- Idempotent chunk application under a per-chunk advisory lock: two clients
-- racing on the same chunk (e.g. a resumed run overlapping a still-finishing
-- one) serialise here and the second one rewrites the same raw_id range.
DELETE FROM public.table2 WHERE id_column_2 BETWEEN :lo AND :hi;
DELETE FROM public.table5 WHERE id_column_2 BETWEEN :lo AND :hi;
DELETE FROM public.table6 WHERE id_column_2 BETWEEN :lo AND :hi;
DELETE FROM public.table1 WHERE id_column_3 BETWEEN :lo AND :hi;

INSERT INTO public.table1
    (id_column_1, id_column_2, datetime_column_1, integer_column_1,
     integer_column_3, integer_column_7, id_column_3, id_column_4)
SELECT s.raw_id, s.id1, s.dt1, s.max_int2, s.num2, s.num1, s.raw_id,
       dimension_row.id_column_1
FROM pgdm_chunk_stage s
JOIN public.table3 AS dimension_row
  ON dimension_row.text_column_1 = BTRIM(s.t1)
 AND dimension_row.text_column_2 = 'SYNTHETIC/REFERENCE'
 AND dimension_row.numeric_column_1 IS NULL
 AND dimension_row.text_column_3 = LEFT(UPPER(BTRIM(s.t2)), 1)
 AND dimension_row.text_column_4 = RIGHT(UPPER(BTRIM(s.t2)), 1);

INSERT INTO public.table5 (numeric_column_1, id_column_2)
SELECT ROUND(NULLIF(BTRIM(s.int_1), '')::numeric, 1), s.raw_id
FROM pgdm_chunk_stage s
WHERE NULLIF(BTRIM(s.int_1), '')::numeric > 0;

INSERT INTO public.table6 (id_column_2, id_column_3)
SELECT s.raw_id, reference_row.id_column_1
FROM pgdm_chunk_stage s
JOIN public.table4 AS reference_row
  ON reference_row.text_column_1 = 'SYNTHETIC/GENERIC'
 AND reference_row.text_column_2 = UPPER(BTRIM(s.t3));

INSERT INTO public.table2
    (id_column_2, integer_column_1, integer_column_2, text_column_1, integer_column_6)
SELECT s.raw_id, p.position_number,
       ROUND(NULLIF(BTRIM(p.weight_text), '')::numeric * 1000)::integer,
       UPPER(BTRIM(p.type_text)),
       CASE WHEN NULLIF(BTRIM(p.gap_text), '')::numeric > 0
            THEN ROUND(NULLIF(BTRIM(p.gap_text), '')::numeric * 1000)::integer END
FROM pgdm_chunk_stage s
CROSS JOIN LATERAL (VALUES
""" + ",\n".join(
    f"    ({i}::smallint, s.int_{i + 1}, s.txt_{i + 3}, s.num_{2 * i + 1}, s.num_{2 * i + 2})"
    for i in range(1, 15)
) + """
) AS p(position_number, declared_number_text, type_text, weight_text, gap_text)
WHERE NULLIF(BTRIM(p.declared_number_text), '')::smallint = p.position_number
  AND NULLIF(BTRIM(p.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(p.type_text)) IN ('X', 'Y', 'Z');
""".strip()

RUNTIME_DDL = f"""
CREATE SCHEMA IF NOT EXISTS {RUNTIME_SCHEMA};
CREATE TABLE IF NOT EXISTS {RUNTIME_SCHEMA}.expansion_jobs (
    job_key text PRIMARY KEY,
    database_name text NOT NULL,
    source_table text NOT NULL,
    raw_schemas text[] NOT NULL,
    destination_signature text NOT NULL,
    scope_min_raw_id bigint,
    scope_max_raw_id bigint,
    chunk_rows integer NOT NULL,
    status text NOT NULL,
    index_state text NOT NULL DEFAULT 'present',
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamptz,
    error_text text
);
ALTER TABLE {RUNTIME_SCHEMA}.expansion_jobs
    ADD COLUMN IF NOT EXISTS index_state text NOT NULL DEFAULT 'present';
CREATE TABLE IF NOT EXISTS {RUNTIME_SCHEMA}.expansion_steps (
    job_key text NOT NULL REFERENCES {RUNTIME_SCHEMA}.expansion_jobs(job_key) ON DELETE CASCADE,
    step_name text NOT NULL,
    status text NOT NULL,
    rows_affected bigint,
    seconds double precision,
    finished_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (job_key, step_name)
);
CREATE TABLE IF NOT EXISTS {RUNTIME_SCHEMA}.expansion_chunks (
    job_key text NOT NULL REFERENCES {RUNTIME_SCHEMA}.expansion_jobs(job_key) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    lo_raw_id bigint NOT NULL,
    hi_raw_id bigint NOT NULL,
    rows_affected bigint,
    seconds double precision,
    finished_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (job_key, chunk_index)
);
""".strip()


DROP_INDEXES_SQL = """
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

REBUILD_INDEXES_SQL = """
CREATE UNIQUE INDEX table1_pkey ON public.table1 (id_column_1);
ALTER TABLE public.table1 ADD CONSTRAINT table1_pkey PRIMARY KEY USING INDEX table1_pkey;
CREATE UNIQUE INDEX table1_id_column_3_key ON public.table1 (id_column_3);
ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_3_key UNIQUE USING INDEX table1_id_column_3_key;

CREATE UNIQUE INDEX table2_pkey ON public.table2 (id_column_1);
ALTER TABLE public.table2 ADD CONSTRAINT table2_pkey PRIMARY KEY USING INDEX table2_pkey;
CREATE UNIQUE INDEX table2_id_column_2_integer_column_1_key ON public.table2 (id_column_2, integer_column_1);
ALTER TABLE public.table2 ADD CONSTRAINT table2_id_column_2_integer_column_1_key UNIQUE USING INDEX table2_id_column_2_integer_column_1_key;

CREATE UNIQUE INDEX table3_pkey ON public.table3 (id_column_1);
ALTER TABLE public.table3 ADD CONSTRAINT table3_pkey PRIMARY KEY USING INDEX table3_pkey;

CREATE UNIQUE INDEX table4_pkey ON public.table4 (id_column_1);
ALTER TABLE public.table4 ADD CONSTRAINT table4_pkey PRIMARY KEY USING INDEX table4_pkey;

CREATE UNIQUE INDEX table5_pkey ON public.table5 (id_column_1);
ALTER TABLE public.table5 ADD CONSTRAINT table5_pkey PRIMARY KEY USING INDEX table5_pkey;
CREATE UNIQUE INDEX table5_id_column_2_when_id_column_3_null_key ON public.table5 (id_column_2) WHERE id_column_3 IS NULL;
CREATE UNIQUE INDEX table5_id_column_3_not_null_key ON public.table5 (id_column_3) WHERE id_column_3 IS NOT NULL;

CREATE UNIQUE INDEX table6_pkey ON public.table6 (id_column_1);
ALTER TABLE public.table6 ADD CONSTRAINT table6_pkey PRIMARY KEY USING INDEX table6_pkey;
CREATE UNIQUE INDEX table6_id_column_2_id_column_3_key ON public.table6 (id_column_2, id_column_3);
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_2_id_column_3_key UNIQUE USING INDEX table6_id_column_2_id_column_3_key;

ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_3_fkey FOREIGN KEY (id_column_3) REFERENCES public.raw_data(raw_id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_4_fkey FOREIGN KEY (id_column_4) REFERENCES public.table3(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table2 ADD CONSTRAINT table2_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table5 ADD CONSTRAINT table5_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_3_fkey FOREIGN KEY (id_column_3) REFERENCES public.table4(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
""".strip()


def indexes_present(runner) -> bool:
    output = runner(
        "SELECT COUNT(*) FROM pg_constraint "
        "WHERE conrelid = 'public.table1'::regclass AND conname = 'table1_pkey';"
    )
    return int(output.strip().splitlines()[-1]) > 0


def drop_indexes(runner):
    runner(f"BEGIN;\nSET LOCAL client_min_messages = warning;\n{DROP_INDEXES_SQL}\nCOMMIT;")


def rebuild_indexes(runner):
    started = time.perf_counter()
    runner(f"BEGIN;\nSET LOCAL client_min_messages = warning;\n{REBUILD_INDEXES_SQL}\nCOMMIT;")
    return time.perf_counter() - started


@dataclass
class Job:
    key: str
    min_raw_id: int
    max_raw_id: int
    chunk_rows: int


class PsqlRunner:
    """Execute SQL through local psql, mirroring the app's SSH runner contract."""

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = str(port)
        self.user = user
        self.password = password
        self.database = database

    def __call__(self, script: str, database: str | None = None) -> str:
        env = dict(os.environ)
        env["PGPASSWORD"] = self.password
        env["PGPORT"] = self.port
        env["PGHOST"] = self.host
        command = [
            "psql", "-h", self.host, "-p", self.port, "-U", self.user,
            "-d", database or self.database, "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-f", "-",
        ]
        result = subprocess.run(
            command, input=script, capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout


def _scope_sql(raw_schemas, alias="s") -> str:
    prefix = f"{alias}." if alias else ""
    return f"{prefix}raw_schema IN (" + ", ".join(
        "'" + str(v).replace("'", "''") + "'" for v in raw_schemas
    ) + ")"


def destination_signature(destinations) -> str:
    payload = json.dumps(
        [
            {"table": d.get("table_name"), "sql": d.get("sql") or ""}
            for d in destinations
        ],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_job(runner, database, source, raw_schemas, destinations, chunk_rows) -> Job:
    scope = _scope_sql(raw_schemas)
    sql = f"""
SELECT COALESCE(MIN(raw_id), 0)::text || '|' || COALESCE(MAX(raw_id), 0)::text
FROM public.{source} s WHERE {scope};
"""
    output = runner(sql).strip().splitlines()[-1]
    lo, hi = (int(part) for part in output.split("|"))
    key = hashlib.sha256(
        json.dumps(
            {
                "db": database,
                "source": source,
                "raw_schemas": [str(v) for v in raw_schemas],
                "destinations": destination_signature(destinations),
                "min": lo,
                "max": hi,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:24]
    return Job(key=key, min_raw_id=lo, max_raw_id=hi, chunk_rows=chunk_rows)


def ensure_runtime(runner):
    runner(RUNTIME_DDL)


def job_status(runner, job: Job) -> tuple[str | None, int]:
    sql = f"""
SELECT COALESCE((SELECT status FROM {RUNTIME_SCHEMA}.expansion_jobs WHERE job_key = '{job.key}'), '')
    || '|' ||
   (SELECT COALESCE(COUNT(*), 0) FROM {RUNTIME_SCHEMA}.expansion_chunks WHERE job_key = '{job.key}');
"""
    output = runner(sql).strip().splitlines()[-1]
    status, count = output.split("|")
    return (status or None), int(count)


def register_job(runner, database, source, raw_schemas, destinations, job: Job):
    scope_literal = "ARRAY[" + ", ".join(
        "'" + str(v).replace("'", "''") + "'" for v in raw_schemas
    ) + "]::text[]"
    sql = f"""
INSERT INTO {RUNTIME_SCHEMA}.expansion_jobs
    (job_key, database_name, source_table, raw_schemas, destination_signature,
     scope_min_raw_id, scope_max_raw_id, chunk_rows, status)
VALUES
    ('{job.key}', '{database}', '{source}', {scope_literal},
     '{destination_signature(destinations)}', {job.min_raw_id}, {job.max_raw_id},
     {job.chunk_rows}, 'running')
ON CONFLICT (job_key) DO UPDATE
    SET status = CASE
            WHEN {RUNTIME_SCHEMA}.expansion_jobs.status = 'completed' THEN 'completed'
            ELSE 'running'
        END,
        updated_at = clock_timestamp();
"""
    runner(sql)


def completed_chunks(runner, job: Job) -> set[int]:
    output = runner(
        f"SELECT chunk_index FROM {RUNTIME_SCHEMA}.expansion_chunks "
        f"WHERE job_key = '{job.key}' ORDER BY chunk_index;"
    )
    return {int(line) for line in output.splitlines() if line.strip()}


def record_step(runner, job: Job, name, status, rows, seconds):
    runner(
        f"""
INSERT INTO {RUNTIME_SCHEMA}.expansion_steps (job_key, step_name, status, rows_affected, seconds)
VALUES ('{job.key}', '{name}', '{status}', {rows if rows is not None else 'NULL'}, {seconds})
ON CONFLICT (job_key, step_name) DO UPDATE
    SET status = EXCLUDED.status, rows_affected = EXCLUDED.rows_affected,
        seconds = EXCLUDED.seconds, finished_at = clock_timestamp();
"""
    )


def reference_done(runner, job: Job) -> bool:
    output = runner(
        f"SELECT COUNT(*) FROM {RUNTIME_SCHEMA}.expansion_steps "
        f"WHERE job_key = '{job.key}' AND step_name = 'references' AND status = 'done';"
    )
    return int(output.strip().splitlines()[-1]) > 0


def run_references(runner, job: Job, source, raw_schemas):
    """Populate table3/table4 exactly once, atomically with the checkpoint row."""
    scope = _scope_sql(raw_schemas)
    body = REFERENCE_SQL.replace("__SOURCE__", source).replace("__SCOPE__", scope)
    started = time.perf_counter()
    script = f"""
BEGIN;
SET LOCAL client_min_messages = warning;
SET LOCAL jit = off;
{body}
INSERT INTO {RUNTIME_SCHEMA}.expansion_steps (job_key, step_name, status, rows_affected, seconds)
VALUES ('{job.key}', 'references', 'done',
        (SELECT count(*) FROM public.table3) + (SELECT count(*) FROM public.table4), 0)
ON CONFLICT (job_key, step_name) DO UPDATE
    SET status = 'done', rows_affected = EXCLUDED.rows_affected, finished_at = clock_timestamp();
COMMIT;
"""
    runner(script)
    return time.perf_counter() - started


def chunk_bounds(job: Job):
    index = 0
    lo = job.min_raw_id
    while lo <= job.max_raw_id:
        hi = min(lo + job.chunk_rows - 1, job.max_raw_id)
        yield index, lo, hi
        index += 1
        lo = hi + 1


def run_chunk(runner, job: Job, index, lo, hi, source, raw_schemas):
    scope = _scope_sql(raw_schemas)
    fill = STAGE_FILL.replace("__SOURCE__", source).replace("__SCOPE__", _scope_sql(raw_schemas, ""))
    fill = fill.replace(":lo", str(lo)).replace(":hi", str(hi))
    chunk_main = CHUNK_MAIN.replace(":lo", str(lo)).replace(":hi", str(hi))
    started = time.perf_counter()
    script = f"""
BEGIN;
SET LOCAL client_min_messages = warning;
SET LOCAL jit = off;
SET LOCAL synchronous_commit = on;
SET LOCAL application_name = 'pgdm_expand:{job.key}';
SELECT pg_advisory_xact_lock(hashtextextended('{job.key}:chunk:{index}', 0));
{STAGE_DDL}
{fill}
{chunk_main}
INSERT INTO {RUNTIME_SCHEMA}.expansion_chunks
    (job_key, chunk_index, lo_raw_id, hi_raw_id, rows_affected, seconds)
VALUES ('{job.key}', {index}, {lo}, {hi},
        (SELECT count(*) FROM pgdm_chunk_stage), 0)
ON CONFLICT (job_key, chunk_index) DO NOTHING;
COMMIT;
"""
    runner(script)
    elapsed = time.perf_counter() - started
    runner(
        f"UPDATE {RUNTIME_SCHEMA}.expansion_chunks SET seconds = {elapsed} "
        f"WHERE job_key = '{job.key}' AND chunk_index = {index};"
    )
    return elapsed


def sync_identity(runner):
    runner(
        """
SELECT setval(pg_get_serial_sequence('public.table1', 'id_column_1'),
              COALESCE((SELECT max(id_column_1) FROM public.table1), 1), true);
"""
    )


def job_totals(runner, job: Job):
    sql = f"""
SELECT
    (SELECT count(*) FROM {RUNTIME_SCHEMA}.expansion_chunks WHERE job_key = '{job.key}')::text
    || '|' ||
    (SELECT COALESCE(SUM(rows_affected), 0) FROM {RUNTIME_SCHEMA}.expansion_chunks WHERE job_key = '{job.key}')::text
    || '|' ||
    (SELECT COALESCE(SUM(seconds), 0) FROM {RUNTIME_SCHEMA}.expansion_chunks WHERE job_key = '{job.key}')::text;
"""
    output = runner(sql).strip().splitlines()[-1]
    chunks, rows, seconds = output.split("|")
    return int(chunks), int(rows), float(seconds)


def verify(runner, source, raw_schemas):
    """Cheap structural verification of the destination set."""
    scope = _scope_sql(raw_schemas)
    sql = f"""
SELECT json_build_object(
  'source_rows', (SELECT count(*) FROM public.{source} s WHERE {scope}),
  'table1_rows', (SELECT count(*) FROM public.table1),
  'table1_distinct_raw', (SELECT count(DISTINCT id_column_3) FROM public.table1),
  'table1_missing_raw', (SELECT count(*) FROM public.{source} s WHERE {scope}
        AND NOT EXISTS (SELECT 1 FROM public.table1 t WHERE t.id_column_3 = s.raw_id)),
  'table1_orphan_raw', (SELECT count(*) FROM public.table1 t
        WHERE NOT EXISTS (SELECT 1 FROM public.{source} s WHERE s.raw_id = t.id_column_3 AND {scope})),
  'table2_rows', (SELECT count(*) FROM public.table2),
  'table2_orphan_parent', (SELECT count(*) FROM public.table2 c
        WHERE NOT EXISTS (SELECT 1 FROM public.table1 p WHERE p.id_column_1 = c.id_column_2)),
  'table3_rows', (SELECT count(*) FROM public.table3),
  'table4_rows', (SELECT count(*) FROM public.table4),
  'table5_rows', (SELECT count(*) FROM public.table5),
  'table6_rows', (SELECT count(*) FROM public.table6)
)::text;
"""
    output = runner(sql).strip().splitlines()[-1]
    return json.loads(output)


def run(database, source, raw_schemas, destinations, chunk_rows, runner,
        resume=True, verify_after=True, log=print) -> dict:
    ensure_runtime(runner)
    job = build_job(runner, database, source, raw_schemas, destinations, chunk_rows)
    status, done_before = job_status(runner, job)
    if status in ("completed", "data-complete"):
        log(f"job {job.key} is already completed; nothing to do "
            f"(use --force to run again after manual cleanup)")
        return {"job": job.key, "status": "already-completed", "resumed": True}
    if status and not resume:
        raise RuntimeError(
            f"job {job.key} is in status {status!r}; rerun with --resume to continue"
        )
    resumed = bool(status)
    register_job(runner, database, source, raw_schemas, destinations, job)
    log(f"job {job.key}: range {job.min_raw_id}..{job.max_raw_id}, "
        f"chunk {chunk_rows}, resumed={resumed}, completed_chunks={done_before}")

    if not reference_done(runner, job):
        seconds = run_references(runner, job, source, raw_schemas)
        log(f"references: done in {seconds:.3f}s")
    else:
        log("references: already done, skipping")

    completed = completed_chunks(runner, job)
    total_chunks = sum(1 for _ in chunk_bounds(job))
    remaining = total_chunks - len(completed)

    # Bulk-load mode: unique indexes / FKs are dropped once, the chunks are
    # loaded without per-row index maintenance, then everything is rebuilt and
    # re-validated before the version step.  Because the job row records the
    # state, an interrupted run always resumes to a consistent index set.
    bulk = not indexes_present(runner)
    if remaining == 0 and indexes_present(runner):
        log("indexes: all chunks already applied and indexes present; skipping bulk phase")
    elif not bulk:
        runner(
            f"UPDATE {RUNTIME_SCHEMA}.expansion_jobs SET index_state = 'dropping', "
            f"updated_at = clock_timestamp() WHERE job_key = '{job.key}';"
        )
        drop_indexes(runner)
        log("indexes: dropped for bulk load (rebuilt at the end)")
        runner(
            f"UPDATE {RUNTIME_SCHEMA}.expansion_jobs SET index_state = 'dropped', "
            f"updated_at = clock_timestamp() WHERE job_key = '{job.key}';"
        )
    else:
        log("indexes: already dropped by an earlier run, will rebuild at the end")

    for index, lo, hi in chunk_bounds(job):
        if index in completed:
            continue
        seconds = run_chunk(runner, job, index, lo, hi, source, raw_schemas)
        log(f"chunk {index + 1}/{total_chunks} [{lo}..{hi}]: {seconds:.3f}s")

    # A crash can happen *after* the rebuild transaction commits but before the
    # job/index_state row is updated.  Detect that case so a resume does not try
    # to create indexes that already exist (or re-validate FKs unnecessarily).
    if indexes_present(runner):
        rebuild_seconds = 0.0
        log("indexes: already present (rebuild committed before the crash), skipping")
    else:
        rebuild_seconds = rebuild_indexes(runner)
        log(f"indexes: rebuilt and foreign keys re-validated in {rebuild_seconds:.3f}s")
    runner(
        f"UPDATE {RUNTIME_SCHEMA}.expansion_jobs SET index_state = 'present', "
        f"updated_at = clock_timestamp() WHERE job_key = '{job.key}';"
    )

    sync_identity(runner)
    chunks, rows, seconds = job_totals(runner, job)
    log(f"data phase: {chunks} chunks, {rows} source rows, {seconds:.3f}s summed")

    result = {"job": job.key, "status": "data-complete", "resumed": resumed,
              "chunks": chunks, "source_rows": rows,
              "chunk_seconds": seconds,
              "index_rebuild_seconds": rebuild_seconds}
    if verify_after:
        result["verification"] = verify(runner, source, raw_schemas)
        log("verification: " + json.dumps(result["verification"], sort_keys=True))
    runner(
        f"UPDATE {RUNTIME_SCHEMA}.expansion_jobs SET status = 'data-complete', "
        f"updated_at = clock_timestamp() WHERE job_key = '{job.key}';"
    )
    return result


def mark_completed(runner, job: Job):
    runner(
        f"UPDATE {RUNTIME_SCHEMA}.expansion_jobs SET status = 'completed', "
        f"completed_at = clock_timestamp(), updated_at = clock_timestamp() "
        f"WHERE job_key = '{job.key}';"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.getenv("PGDATABASE", "kaggle_challenge"))
    parser.add_argument("--host", default=os.getenv("PGHOST", "127.0.0.1"))
    parser.add_argument("--port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--password", default=os.getenv("PGPASSWORD", ""))
    parser.add_argument("--source", default="raw_data")
    parser.add_argument("--raw-schema", action="append", dest="raw_schemas")
    parser.add_argument("--chunk-rows", type=int, default=200_000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--recipes", default="SQL files")
    args = parser.parse_args()

    raw_schemas = args.raw_schemas or ["group001"]
    recipe_dir = Path(args.recipes)
    destinations = [
        {"table_name": f"public.{name}", "sql": (recipe_dir / f).read_text(encoding="utf-8")}
        for f, name in (
            ("01_table3.sql", "table3"), ("02_table4.sql", "table4"),
            ("03_table1.sql", "table1"), ("04_table5.sql", "table5"),
            ("05_table6.sql", "table6"), ("06_table2.sql", "table2"),
        )
    ]
    runner = PsqlRunner(args.host, args.port, args.user, args.password, args.db)
    result = run(
        args.db, args.source, raw_schemas, destinations, args.chunk_rows, runner,
        resume=args.resume, verify_after=True,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "job"}, indent=2))


if __name__ == "__main__":
    main()
