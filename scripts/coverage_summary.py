# renders the coverage each suite reached as a markdown table for the run summary
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

SERVICES = ("identity", "catalog", "sales", "payments", "ticketing", "entry", "audit")

_EXPECTED_ARGS = 2

AREAS = (
    ("Features", "src/features"),
    ("Routes", "src/routes"),
    ("Components", "src/components"),
    ("Library", "src/lib"),
    ("Store", "src/store"),
    ("i18n", "src/i18n"),
    ("Config", "src/config"),
    ("Hooks", "src/hooks"),
)


# formats a covered over total pair as a percentage
def _pct(covered: int, total: int) -> str:
    return f"{100 * covered / total:.1f} %" if total else "n/a"


# reports the statement coverage each backend service reached under its unit suite
def api_summary() -> list[str]:
    rows = ["| Service | Statements | Missed | Coverage |", "|---|---:|---:|---:|"]
    total = missed = 0
    for service in SERVICES:
        report = ROOT / "apps/api/services" / service / "coverage.json"
        if not report.exists():
            rows.append(f"| {service} | — | — | not measured |")
            continue
        totals = json.loads(report.read_text())["totals"]
        n, m = totals["num_statements"], totals["missing_lines"]
        total += n
        missed += m
        rows.append(f"| {service} | {n} | {m} | {_pct(n - m, n)} |")
    overall = _pct(total - missed, total)
    rows.append(f"| **Total** | **{total}** | **{missed}** | **{overall}** |")
    return rows


# reports the statement coverage the client reached, broken down by area
def app_summary() -> list[str]:
    report = ROOT / "apps/app/coverage/coverage-summary.json"
    data = json.loads(report.read_text())
    tally = {name: [0, 0] for name, _ in AREAS}
    rest = [0, 0]
    for path, entry in data.items():
        if path == "total":
            continue
        rel = path.replace("\\", "/")
        rel = "src/" + rel.split("src/", 1)[1] if "src/" in rel else rel
        stats = entry["statements"]
        for name, prefix in AREAS:
            if rel.startswith(prefix + "/"):
                tally[name][0] += stats["total"]
                tally[name][1] += stats["covered"]
                break
        else:
            rest[0] += stats["total"]
            rest[1] += stats["covered"]

    rows = ["| Area | Statements | Coverage |", "|---|---:|---:|"]
    for name, _ in AREAS:
        total, covered = tally[name]
        if total:
            rows.append(f"| {name} | {total} | {_pct(covered, total)} |")
    if rest[0]:
        rows.append(f"| Other | {rest[0]} | {_pct(rest[1], rest[0])} |")
    overall = data["total"]["statements"]
    gap = overall["total"] - overall["covered"]
    rows.append(f"| **Total** | **{overall['total']}** | **{overall['pct']:.1f} %** |")
    rows.append("")
    rows.append(f"{gap} of {overall['total']} statements are never reached.")
    return rows


# picks the suite to summarise from the single argument the workflow passes
def main() -> int:
    if len(sys.argv) != _EXPECTED_ARGS or sys.argv[1] not in {"api", "app"}:
        print("usage: coverage_summary.py api|app", file=sys.stderr)
        return 2
    rows = api_summary() if sys.argv[1] == "api" else app_summary()
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
