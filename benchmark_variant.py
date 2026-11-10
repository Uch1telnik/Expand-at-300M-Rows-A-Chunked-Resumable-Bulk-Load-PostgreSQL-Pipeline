"""Benchmark a fused SQL file inside the service timing envelope.

Usage: python3 benchmark_variant.py <sqlfile> [label] [--work_mem=256MB] [--nomaterial]
"""
import json
import sys
from pathlib import Path

from services.postgres_service import PostgresAdminService

ROOT = Path(__file__).resolve().parent


def main():
    sqlfile = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else "variant"
    settings = [a for a in sys.argv[3:] if a.startswith("--")]
    fused = (ROOT / sqlfile).read_text(encoding="utf-8").strip().rstrip(";")
    if "--nomaterial" in settings:
        fused = fused.replace("AS MATERIALIZED", "AS NOT MATERIALIZED")
    service = PostgresAdminService()
    service.connect(
        host="127.0.0.1", ssh_port=22, ssh_username="root", ssh_password="rootpass",
        postgres_port=5433, sql_username="challenge", sql_password="challengepass",
    )
    lock_sql = (
        "LOCK TABLE public.table1, public.table2, public.table3, public.table4, "
        "public.table5, public.table6 IN SHARE ROW EXCLUSIVE MODE;"
    )
    manifest_sql = (
        "CREATE TEMP TABLE pgdm_cross_table_hash_manifest ON COMMIT DROP AS "
        "SELECT raw_schema::text, raw_hash::text, COUNT(*)::bigint AS row_count "
        "FROM public.raw_data WHERE raw_schema IN ('group001') "
        "GROUP BY raw_schema, raw_hash;"
    )
    timing_table = """
CREATE TEMP TABLE pgdm_expansion_timings (
    sequence_number integer PRIMARY KEY, stage_key text NOT NULL, item_name text NOT NULL,
    started_at timestamptz NOT NULL, finished_at timestamptz, rows_affected bigint,
    destination_name text, statement_index integer
) ON COMMIT PRESERVE ROWS;"""
    result_sql = """
SELECT json_build_object('pgdm_expansion_timings', COALESCE(json_agg(json_build_object(
 'sequence', sequence_number, 'stage', stage_key, 'name', item_name,
 'duration_seconds', EXTRACT(EPOCH FROM (finished_at - started_at)),
 'rows', rows_affected, 'destination', destination_name, 'statement_index', statement_index
) ORDER BY sequence_number), '[]'::json))::text FROM pg_temp.pgdm_expansion_timings;"""
    extra = "".join(
        f"SET LOCAL {s[2:].split('=')[0]} = '{s.split('=', 1)[1]}';\n"
        for s in settings
        if s.startswith("--") and "=" in s
    )
    script = (
        timing_table
        + "\nBEGIN ISOLATION LEVEL REPEATABLE READ;\n"
        + "INSERT INTO pg_temp.pgdm_expansion_timings VALUES (1,'execute','Initialize database transaction',clock_timestamp(),NULL,NULL,NULL,NULL);\n"
        + "SET LOCAL client_min_messages = warning;\n"
        + "SET LOCAL jit = off;\n"
        + extra
        + "UPDATE pg_temp.pgdm_expansion_timings SET finished_at=clock_timestamp() WHERE sequence_number=1;\n"
        + "INSERT INTO pg_temp.pgdm_expansion_timings VALUES (2,'execute','Acquire destination table locks',clock_timestamp(),NULL,NULL,NULL,NULL);\n"
        + lock_sql
        + "\nUPDATE pg_temp.pgdm_expansion_timings SET finished_at=clock_timestamp() WHERE sequence_number=2;\n"
        + "INSERT INTO pg_temp.pgdm_expansion_timings VALUES (3,'execute','Scan source and build dependency manifest',clock_timestamp(),NULL,NULL,NULL,NULL);\n"
        + manifest_sql
        + "\nUPDATE pg_temp.pgdm_expansion_timings SET finished_at=clock_timestamp() WHERE sequence_number=3;\n"
        + f"INSERT INTO pg_temp.pgdm_expansion_timings VALUES (4,'execute','Fused single-pass expansion ({sqlfile})',clock_timestamp(),NULL,NULL,NULL,NULL);\n"
        + fused
        + ";\nUPDATE pg_temp.pgdm_expansion_timings SET finished_at=clock_timestamp() WHERE sequence_number=4;\n"
        + "INSERT INTO pg_temp.pgdm_expansion_timings VALUES (9000,'execute','Commit expansion transaction',clock_timestamp(),NULL,NULL,NULL,NULL);\n"
        + "COMMIT;\n"
        + "UPDATE pg_temp.pgdm_expansion_timings SET finished_at=clock_timestamp() WHERE sequence_number=9000;\n"
        + result_sql
        + "\nDROP TABLE pg_temp.pgdm_expansion_timings;\n"
    )
    command = (
        f"psql -h localhost -U {service.sql_username} -d kaggle_challenge "
        "-X -qAt -v ON_ERROR_STOP=1 -f -"
    )
    output = service.run_remote_command(command, stdin_text=script)
    items = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{") and "pgdm_expansion_timings" in line:
            items = json.loads(line)["pgdm_expansion_timings"]
    if items is None:
        print(output)
        raise SystemExit("no timings")
    total = 0.0
    for item in items:
        sec = float(item["duration_seconds"])
        total += sec
        print(f"{item['sequence']:>5} {item['name']:<60} {sec:>9.3f}s")
    print(f">>> {label} MEASURED PROCESSING TOTAL: {total:.3f} s")


if __name__ == "__main__":
    main()
