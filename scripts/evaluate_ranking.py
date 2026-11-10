import argparse
import json
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path

from backend.app.domain.models import FlightSegment, Itinerary
from backend.app.ranking.scoring import RankingWeights, rank_destinations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = PROJECT_ROOT / "data" / "ranking_eval_scenarios.json"


def build_itinerary(
    *,
    origin: str,
    destination: str,
    arrival_time: datetime,
    duration_minutes: float,
    stops: int,
    option_index: int,
    traveler_label: str,
) -> Itinerary:
    departure_time = arrival_time - timedelta(minutes=duration_minutes)

    if stops == 0:
        return Itinerary(
            segments=[
                FlightSegment(
                    flight_number=f"DL{traveler_label}{option_index}0",
                    operating_carrier="DL",
                    origin=origin,
                    destination=destination,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                )
            ]
        )

    segment_count = stops + 1
    total_connection_minutes = 45 * stops
    air_minutes = max(duration_minutes - total_connection_minutes, segment_count)
    leg_minutes = air_minutes / segment_count

    segments = []
    current_origin = origin
    current_departure = departure_time

    for leg_index in range(segment_count):
        current_destination = (
            destination
            if leg_index == segment_count - 1
            else f"X{traveler_label}{option_index}{leg_index}"
        )
        leg_arrival = current_departure + timedelta(minutes=leg_minutes)

        segments.append(
            FlightSegment(
                flight_number=f"DL{traveler_label}{option_index}{leg_index}",
                operating_carrier="DL",
                origin=current_origin,
                destination=current_destination,
                departure_time=current_departure,
                arrival_time=(
                    arrival_time
                    if leg_index == segment_count - 1
                    else leg_arrival
                ),
            )
        )

        current_origin = current_destination
        current_departure = leg_arrival + timedelta(minutes=45)

    return Itinerary(segments=segments)


def build_candidate_pairs(candidate: dict) -> list[tuple[Itinerary, Itinerary]]:
    base_arrival = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    gap = candidate["arrival_gap_minutes"]
    total_travel = candidate["total_travel_time_minutes"]
    total_stops = candidate["total_stops"]

    travel_a = total_travel / 2
    travel_b = total_travel - travel_a
    stops_a = total_stops // 2
    stops_b = total_stops - stops_a

    option_count = candidate["backup_layers"] + 1

    itineraries_a = [
        build_itinerary(
            origin="AAA",
            destination=candidate["destination"],
            arrival_time=base_arrival,
            duration_minutes=travel_a,
            stops=stops_a,
            option_index=i,
            traveler_label="A",
        )
        for i in range(option_count)
    ]
    itineraries_b = [
        build_itinerary(
            origin="BBB",
            destination=candidate["destination"],
            arrival_time=base_arrival + timedelta(minutes=gap),
            duration_minutes=travel_b,
            stops=stops_b,
            option_index=i,
            traveler_label="B",
        )
        for i in range(option_count)
    ]

    return list(product(itineraries_a, itineraries_b))


def evaluate_scenario(scenario: dict) -> dict:
    pairs = []

    for candidate in scenario["candidates"]:
        pairs.extend(build_candidate_pairs(candidate))

    weights = RankingWeights(**scenario["weights"])
    ranked = rank_destinations(pairs, weights)

    predicted = ranked[0][0] if ranked else None
    passed = predicted == scenario["expected_destination"]

    return {
        "name": scenario["name"],
        "description": scenario["description"],
        "expected": scenario["expected_destination"],
        "predicted": predicted,
        "passed": passed,
        "top_score": ranked[0][3] if ranked else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic meetup ranking on curated tradeoff scenarios."
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Path to the ranking evaluation scenario JSON file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args()

    payload = json.loads(args.scenarios.read_text(encoding="utf-8"))
    results = [evaluate_scenario(scenario) for scenario in payload["scenarios"]]

    passed = sum(result["passed"] for result in results)
    total = len(results)
    accuracy = passed / total if total else 0.0

    summary = {
        "passed": passed,
        "total": total,
        "accuracy": accuracy,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print("Ranking evaluation")
    print("=" * 72)

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status:4}  {result['name']}: "
            f"expected={result['expected']} predicted={result['predicted']}"
        )

    print("-" * 72)
    print(f"Result: {passed}/{total} expected outcomes ({accuracy:.1%})")


if __name__ == "__main__":
    main()
