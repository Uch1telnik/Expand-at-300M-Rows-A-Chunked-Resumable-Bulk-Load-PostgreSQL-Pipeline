"""Linux-side runner: expansion over SSH to localhost, prints measured total.

Avoids the Windows->WSL localhost proxy, which resets long-lived SSH channels.
"""
import sys
from datetime import datetime
from pathlib import Path

from services.postgres_service import PostgresAdminService

ROOT = Path(__file__).resolve().parent
RECIPES = [
    ("01_table3.sql", "public.table3"),
    ("02_table4.sql", "public.table4"),
    ("03_table1.sql", "public.table1"),
    ("04_table5.sql", "public.table5"),
    ("05_table6.sql", "public.table6"),
    ("06_table2.sql", "public.table2"),
]


def measured_total(report):
    return sum(
        max(float(item.get("seconds") or 0.0), 0.0)
        for item in (report.get("items") or [])
        if item.get("include_in_total", True)
    )


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else "kaggle_challenge"
    folder = sys.argv[2] if len(sys.argv) > 2 else "SQL files"
    label = sys.argv[3] if len(sys.argv) > 3 else "run"
    service = PostgresAdminService()
    service.connect(
        host="127.0.0.1", ssh_port=22, ssh_username="root", ssh_password="rootpass",
        postgres_port=5433, sql_username="challenge", sql_password="challengepass",
    )
    destinations = [
        {"table_name": t, "version_title": "Synthetic expansion",
         "sql": (ROOT / folder / n).read_text(encoding="utf-8")}
        for n, t in RECIPES
    ]
    report = service.create_cross_table_expansion_timing_report(
        db, "public.raw_data", ["group001"], [t for _n, t in RECIPES]
    )
    result = service.execute_cross_table_expansion(
        db, "public.raw_data", ["group001"], destinations, timing_report=report
    )
    report = result["timing_report"]
    report["completed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    total = measured_total(report)
    lines = []
    for item in report.get("items") or []:
        if item.get("include_in_total", True):
            lines.append(
                f"{item.get('stage'):<8} {item.get('name')[:55]:<55} "
                f"{float(item.get('seconds') or 0):>9.3f}s rows={item.get('rows')}"
            )
    text = "\n".join(lines) + f"\n\n>>> {label} MEASURED PROCESSING TOTAL: {total:.3f} s\n"
    Path(f"{label}_report.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
