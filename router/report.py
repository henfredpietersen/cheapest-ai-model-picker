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
    report = {"rows": rows}
    (ROOT / "report.json").write_text(json.dumps(report, indent=2))
    print(f"{'difficulty':<10} {'budget':>8} {'backend':<14} {'cost':>10} {'ms':>6}")
    for row in rows:
        print(f"{row['difficulty']:<10} {row['budget_usd']:>8} {row['backend']:<14} {row['cost_usd']:>10} {row['latency_ms']:>6}")


if __name__ == "__main__":
    main()
