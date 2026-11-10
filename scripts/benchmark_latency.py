import argparse
import json
import os
import statistics
import time

import httpx


DEFAULT_PAYLOAD = {
    "traveler_a": {
        "origin": "JFK",
        "depart_after": "2026-11-13T17:00:00-05:00",
        "depart_before": "2026-11-13T23:59:00-05:00",
        "return_after": "2026-11-15T15:00:00-05:00",
        "return_before": "2026-11-15T20:00:00-05:00",
    },
    "traveler_b": {
        "origin": "SEA",
        "depart_after": "2026-11-13T14:00:00-08:00",
        "depart_before": "2026-11-13T20:00:00-08:00",
        "return_after": "2026-11-15T13:00:00-08:00",
        "return_before": "2026-11-15T20:00:00-08:00",
    },
    "constraints": {
        "max_stops": 1,
        "max_arrival_gap_minutes": 120,
    },
    "weights": {
        "arrival_sync": 4,
        "stops": 2,
        "travel_time": 3,
        "backup_options": 1,
    },
}


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0

    index = (len(ordered) - 1) * percentile_value
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize(latencies_ms: list[float]) -> dict:
    return {
        "requests": len(latencies_ms),
        "mean_ms": statistics.fmean(latencies_ms),
        "median_ms": statistics.median(latencies_ms),
        "p95_ms": percentile(latencies_ms, 0.95),
        "min_ms": min(latencies_ms),
        "max_ms": max(latencies_ms),
    }


def benchmark_local(iterations: int, warmup: int) -> dict:
    os.environ["FLIGHT_PROVIDER"] = "mock"

    from fastapi.testclient import TestClient
    from backend.app.api import app

    with TestClient(app) as client:
        for _ in range(warmup):
            response = client.post("/meetups/search", json=DEFAULT_PAYLOAD)
            response.raise_for_status()

        latencies = []

        for _ in range(iterations):
            started = time.perf_counter()
            response = client.post("/meetups/search", json=DEFAULT_PAYLOAD)
            response.raise_for_status()
            latencies.append((time.perf_counter() - started) * 1000)

    return {
        "mode": "local-testclient",
        "provider": "mock",
        **summarize(latencies),
    }


def benchmark_remote(url: str, iterations: int, warmup: int) -> dict:
    endpoint = f"{url.rstrip('/')}/meetups/search"

    with httpx.Client(timeout=60.0) as client:
        for _ in range(warmup):
            response = client.post(endpoint, json=DEFAULT_PAYLOAD)
            response.raise_for_status()

        latencies = []

        for _ in range(iterations):
            started = time.perf_counter()
            response = client.post(endpoint, json=DEFAULT_PAYLOAD)
            response.raise_for_status()
            latencies.append((time.perf_counter() - started) * 1000)

    return {
        "mode": "remote-http",
        "url": endpoint,
        **summarize(latencies),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Flight Meetup search latency."
    )
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument(
        "--url",
        help=(
            "Optional deployed backend URL. Omit for a quota-safe local "
            "TestClient benchmark using the mock provider."
        ),
    )
    args = parser.parse_args()

    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.warmup < 0:
        parser.error("--warmup cannot be negative")

    if args.url:
        print(
            "WARNING: remote benchmarking calls the deployed backend repeatedly. "
            "Do not use this against a live quota-limited OAG deployment unless "
            "you intentionally want those provider requests."
        )
        result = benchmark_remote(args.url, args.iterations, args.warmup)
    else:
        result = benchmark_local(args.iterations, args.warmup)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
