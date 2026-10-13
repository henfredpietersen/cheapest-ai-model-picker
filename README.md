# model-router

## Problem

Different requests need different models. A cheap local model may be good enough for easy requests, and paying for a large hosted model only makes sense when quality requires it. This repo has one routing policy, "the cheapest backend whose quality clears the bar for this request class, within the per-call budget", plus a probe that measures real latency for a local Ollama model.

Built AI-assisted under my direction. I specified the policy and the probe rules, reviewed the output, and ran the commands shown here.

## How it works

- `router/policy.py`: `route(difficulty, budget_usd)`. Quality bars: easy 0.70, normal 0.80, hard 0.90. The three backends (`local-4bit`, `hosted-small`, `hosted-large`) have **placeholder** cost, latency, and quality constants. These are not measurements.
- `router/report.py`: sweeps the policy over difficulty × budget and writes `policy_rows` to `report.json`.
- `router/probe.py`: if Ollama is running, sends a warm-up call plus N fixed classification prompts to one model and records wall-clock latency, Ollama's server timings, and token counts. It writes `ollama_probe` to `report.json`. If Ollama is down, it records `status: not_measured` and exits 0. Cost and quality are always `null` in the probe: local inference has no per-token price, and the probe runs no eval.

## How to run

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest -q
PYTHONPATH=. python -m router.report
PYTHONPATH=. python -m router.probe                         # uses OLLAMA_HOST, first pulled model
PYTHONPATH=. python -m router.probe --model qwen2.5:1.5b --runs 5
```

## Measured

**Ollama latency: not measured.** Output of `python -m router.probe` in this session (no Ollama in the workspace):

```
not measured: Ollama not reachable at http://localhost:11434: <urlopen error [Errno 111] Connection refused>
wrote .../model-router/report.json
```

Run it on a machine with Ollama running and the median, min, and max latency land in `report.json`.

**Policy sweep (placeholder inputs, not measurements).** Output of `python -m router.report`. Cost is for 200 tokens using the placeholder price.

```
difficulty   budget backend              cost     ms
easy          0.001 local-4bit            0.0    180
easy           0.05 local-4bit            0.0    180
easy            1.0 local-4bit            0.0    180
normal        0.001 hosted-large          0.6    900
normal         0.05 hosted-small         0.03    420
normal          1.0 hosted-small         0.03    420
hard          0.001 hosted-large          0.6    900
hard           0.05 hosted-large          0.6    900
hard            1.0 hosted-large          0.6    900
```

What the sweep shows: when nothing fits the budget, the policy falls back to `hosted-large` and **ignores the budget**. In the rows above, normal@0.001 and hard@0.001/0.05 cost 0.6 against budgets of 0.001 and 0.05. I left the policy unchanged on purpose. It is listed below under what I would not ship.

## Tests

`tests/test_policy.py` (original routing cases) and `tests/test_probe.py`:

- With Ollama down, the probe exits 0, records `not_measured`, writes no latency, and keeps other sections of `report.json` intact.
- A local fake HTTP server in Ollama's response shape tests the measured path's parsing. Its numbers are test inputs, not results.
- Asking for a model that isn't pulled gives `not_measured`.
- `cost_usd` is never filled in.

## What I would not ship

- The placeholder backend constants. Replace them with probe results and an eval score on a shared prompt set.
- The budget-breaking fallback. It should return "over budget" or degrade explicitly rather than silently spend 600× the budget.
- Difficulty as a caller-supplied label. Production needs a classifier, and that classifier needs its own eval.
- A 3-prompt latency probe as a capacity number. It measures one model on one machine with no concurrency.
