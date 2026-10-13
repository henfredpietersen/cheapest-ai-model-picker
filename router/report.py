"""Sweep the policy and write a small report."""

import json
from pathlib import Path

from router.policy import estimate_call, route

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rows = []
    for difficulty in ("easy", "normal", "hard"):
        for budget in (0.001, 0.05, 1.0):
            chosen = route(difficulty, budget_usd=budget)
            rows.append({"difficulty": difficulty, "budget_usd": budget, **estimate_call(chosen)})
    path = ROOT / "report.json"
    report = json.loads(path.read_text()) if path.exists() else {}
    report["policy_rows"] = rows
    report["policy_note"] = "Backend cost, latency and quality are placeholder constants in router/policy.py, not measurements."
    report.pop("rows", None)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{'difficulty':<10} {'budget':>8} {'backend':<14} {'cost':>10} {'ms':>6}")
    for row in rows:
        print(f"{row['difficulty']:<10} {row['budget_usd']:>8} {row['backend']:<14} {row['cost_usd']:>10} {row['latency_ms']:>6}")


if __name__ == "__main__":
    main()
