import argparse
import json
import os
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path

from backend.app.airports.timezones import get_airport_timezone
from backend.app.domain.models import SearchConstraints, TravelerRequest
from backend.app.providers.oag import OAGFlightProvider
from backend.app.providers.schedules import collect_direct_schedules
from backend.app.ranking.scoring import RankingWeights, rank_meeting_destinations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = PROJECT_ROOT / "data" / "oag_eval_scenarios.json"


def parse_local_datetime(
    travel_date: date,
    clock_text: str,
    airport: str,
) -> datetime:
    hour, minute = [int(part) for part in clock_text.split(":")]
    timezone = get_airport_timezone(airport)

    return datetime.combine(
        travel_date,
        dt_time(hour=hour, minute=minute),
        tzinfo=timezone,
    )


def build_traveler(
    config: dict,
    travel_date: date,
) -> TravelerRequest:
    origin = config["origin"].upper()

    return TravelerRequest(
        origin=origin,
        depart_after=parse_local_datetime(
            travel_date,
            config["depart_after"],
            origin,
        ),
        depart_before=parse_local_datetime(
            travel_date,
            config["depart_before"],
            origin,
        ),
    )


def run_once(
    provider: OAGFlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
):
    started = time.perf_counter()

    flights = collect_direct_schedules(
        provider,
        [traveler_a, traveler_b],
    )

    constraints = SearchConstraints(
        max_stops=0,
        max_travel_time_minutes=None,
        max_arrival_gap_minutes=180,
    )

    weights = RankingWeights(
        arrival_sync=0.6,
        stops=0.0,
        travel_time=0.4,
        backup_options=0.2,
    )

    ranked = rank_meeting_destinations(
        flights,
        traveler_a,
        traveler_b,
        constraints,
        weights,
    )

    latency_ms = (time.perf_counter() - started) * 1000

    return {
        "latency_ms": latency_ms,
        "flights_collected": len(flights),
        "common_destinations": len(ranked),
        "top_destinations": [
            {
                "destination": destination,
                "score": round(score, 4),
                "arrival_gap_minutes": round(
                    best_pair.metrics.arrival_gap_minutes,
                    1,
                ),
                "total_travel_time_minutes": round(
                    best_pair.metrics.total_travel_time_minutes,
                    1,
                ),
                "backup_layers": backup_count,
            }
            for destination, best_pair, backup_count, score in ranked[:5]
        ],
    }


def evaluate_scenario(
    config: dict,
    travel_date: date,
    request_budget: int,
) -> dict:
    provider = OAGFlightProvider(
        max_requests=request_budget,
    )

    traveler_a = build_traveler(
        config["traveler_a"],
        travel_date,
    )
    traveler_b = build_traveler(
        config["traveler_b"],
        travel_date,
    )

    before_cold = provider.request_count
    cold = run_once(
        provider,
        traveler_a,
        traveler_b,
    )
    cold_requests = provider.request_count - before_cold

    before_warm = provider.request_count
    warm = run_once(
        provider,
        traveler_a,
        traveler_b,
    )
    warm_requests = provider.request_count - before_warm

    request_savings = (
        1.0 - (warm_requests / cold_requests)
        if cold_requests
        else 0.0
    )

    latency_speedup = (
        cold["latency_ms"] / warm["latency_ms"]
        if warm["latency_ms"] > 0
        else None
    )

    return {
        "name": config["name"],
        "travel_date": travel_date.isoformat(),
        "origins": [
            traveler_a.origin,
            traveler_b.origin,
        ],
        "cold": {
            **cold,
            "oag_http_requests": cold_requests,
        },
        "warm_repeat": {
            **warm,
            "additional_oag_http_requests": warm_requests,
        },
        "cache_request_savings_percent": round(
            request_savings * 100,
            1,
        ),
        "latency_speedup_x": (
            round(latency_speedup, 2)
            if latency_speedup is not None
            else None
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run a small, explicit, quota-bounded evaluation against live "
            "OAG schedules. Direct flights and one-way searches only."
        )
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Travel date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS,
    )
    parser.add_argument(
        "--scenario",
        help="Run only the named scenario instead of the first N scenarios.",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=3,
        help="Maximum number of scenarios to run.",
    )
    parser.add_argument(
        "--request-budget",
        type=int,
        default=25,
        help="Hard OAG HTTP request budget per scenario.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file path for saved results.",
    )
    args = parser.parse_args()

    if os.getenv("RUN_LIVE_OAG_EVAL") != "1":
        raise SystemExit(
            "Live OAG evaluation is disabled by default. "
            "Set RUN_LIVE_OAG_EVAL=1 to confirm intentional quota use."
        )

    if not os.getenv("OAG_API_KEY"):
        raise SystemExit("OAG_API_KEY is not set.")

    if args.max_scenarios <= 0:
        parser.error("--max-scenarios must be positive")

    if args.request_budget <= 0:
        parser.error("--request-budget must be positive")

    travel_date = date.fromisoformat(args.date)
    payload = json.loads(
        args.scenarios.read_text(encoding="utf-8")
    )

    if args.scenario:
        selected = [
            scenario
            for scenario in payload["scenarios"]
            if scenario["name"] == args.scenario
        ]
        if not selected:
            parser.error(f"Unknown scenario: {args.scenario}")
    else:
        selected = payload["scenarios"][: args.max_scenarios]

    print(
        f"Running {len(selected)} live OAG scenario(s) for "
        f"{travel_date.isoformat()} with a hard budget of "
        f"{args.request_budget} OAG HTTP requests per scenario."
    )

    results = []

    failures = []

    for config in selected:
        print(f"\nRunning {config['name']}...")
        try:
            result = evaluate_scenario(
                config,
                travel_date,
                args.request_budget,
            )
        except RuntimeError as exc:
            failure = {
                "name": config["name"],
                "error": str(exc),
            }
            failures.append(failure)
            print(f"  FAILED: {exc}")
            continue

        results.append(result)

        print(
            f"  cold requests: "
            f"{result['cold']['oag_http_requests']}"
        )
        print(
            f"  cold latency: "
            f"{result['cold']['latency_ms']:.1f} ms"
        )
        print(
            f"  flights collected: "
            f"{result['cold']['flights_collected']}"
        )
        print(
            f"  common destinations: "
            f"{result['cold']['common_destinations']}"
        )
        print(
            f"  warm additional requests: "
            f"{result['warm_repeat']['additional_oag_http_requests']}"
        )
        print(
            f"  cache request savings: "
            f"{result['cache_request_savings_percent']:.1f}%"
        )

        if result["cold"]["top_destinations"]:
            print("  top destinations:")
            for item in result["cold"]["top_destinations"]:
                print(
                    f"    {item['destination']}: "
                    f"score={item['score']} "
                    f"gap={item['arrival_gap_minutes']}m "
                    f"travel={item['total_travel_time_minutes']}m "
                    f"backups={item['backup_layers']}"
                )

    total_cold_requests = sum(
        item["cold"]["oag_http_requests"]
        for item in results
    )
    total_warm_requests = sum(
        item["warm_repeat"]["additional_oag_http_requests"]
        for item in results
    )

    scenarios_with_results = sum(
        item["cold"]["common_destinations"] > 0
        for item in results
    )

    summary = {
        "travel_date": travel_date.isoformat(),
        "scenario_count_requested": len(selected),
        "scenario_count_completed": len(results),
        "scenario_count_failed": len(failures),
        "scenarios_with_common_destinations": scenarios_with_results,
        "total_cold_oag_http_requests": total_cold_requests,
        "total_warm_additional_oag_http_requests": total_warm_requests,
        "results": results,
        "failures": failures,
    }

    print("\n" + "=" * 72)
    print(
        f"Coverage: {scenarios_with_results}/{len(results)} completed "
        "scenarios produced at least one common destination"
    )
    if failures:
        print(f"Failed scenarios: {len(failures)}")
    print(
        f"Total cold OAG HTTP requests: {total_cold_requests}"
    )
    print(
        f"Total additional OAG requests on identical repeats: "
        f"{total_warm_requests}"
    )

    rendered = json.dumps(summary, indent=2)

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            rendered + "\n",
            encoding="utf-8",
        )
        print(f"Saved JSON results to {args.output}")
    else:
        print("\nJSON summary:")
        print(rendered)


if __name__ == "__main__":
    main()
