"""Route a prompt to a backend by a cost and quality policy. Backends are faked."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Backend:
    name: str
    usd_per_1k: float
    latency_ms: float
    quality: float


BACKENDS = {
    "local-4bit": Backend("local-4bit", 0.0, 180, 0.72),
    "hosted-small": Backend("hosted-small", 0.15, 420, 0.81),
    "hosted-large": Backend("hosted-large", 3.00, 900, 0.93),
}


def route(difficulty: str, budget_usd: float = 0.01) -> Backend:
    """Pick the cheapest backend whose quality clears the bar inside the per-call budget."""
    bar = {"easy": 0.70, "normal": 0.80, "hard": 0.90}[difficulty]
    eligible = [
        b for b in BACKENDS.values() if b.quality >= bar and (b.usd_per_1k * 0.2) <= budget_usd
    ]
    if not eligible:
        return BACKENDS["hosted-large"]
    return sorted(eligible, key=lambda b: (b.usd_per_1k, b.latency_ms))[0]


def estimate_call(backend: Backend, tokens: int = 200) -> dict:
    return {
        "backend": backend.name,
        "latency_ms": backend.latency_ms,
        "cost_usd": round(backend.usd_per_1k * tokens / 1000, 6),
        "quality": backend.quality,
    }
