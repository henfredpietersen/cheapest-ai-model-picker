# model-router

One policy function, three backends, a cost and quality table. Numbers are measured stand-ins so the routing decision is testable without burning API spend.

## Policy

Pick the cheapest backend whose offline quality clears the bar for the request class, inside the per-call budget.

| class | bar | typical pick at a tight budget | typical pick with budget |
| --- | --- | --- | --- |
| easy | 0.70 | local-4bit ($0, 180 ms, 0.72) | local-4bit |
| normal | 0.80 | falls through if local misses the bar | hosted-small |
| hard | 0.90 | hosted-large | hosted-large |

## Run

```bash
pip install pytest
PYTHONPATH=. pytest -q
PYTHONPATH=. python -m router.report
```

Replace `BACKENDS` with real probe results: same prompt set, three endpoints, record cost, latency, and an eval score. The policy function stays.
