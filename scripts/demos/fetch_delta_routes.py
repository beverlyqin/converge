"""Build the Delta route list used by the demo flight schedule.

Fetches one day of Delta-operated nonstop departures from each airport
through OAG, then keeps only which routes exist and how many flights a
day each has. Flight numbers and times are not saved; the demo schedule
generates its own times from this route list.

Routes are assumed to run in both directions, so departures alone also
give the return routes.

Usage:
    python -m scripts.demos.fetch_delta_routes
    python -m scripts.demos.fetch_delta_routes --airports ATL --request-budget 30

Running with a subset of airports updates only those airports in the
existing output file.
"""

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from backend.app.airports.timezones import get_airport_timezone
from backend.app.domain.models import FlightSegment
from backend.app.providers.oag import OAGFlightProvider

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AIRPORTS = ["JFK", "LGA", "ATL", "LAX"]
DEFAULT_OUTPUT = ROOT / "backend" / "data" / "delta_routes.json"


def default_sample_date(today: date | None = None) -> date:
    """A Wednesday about three weeks out, skipping the holiday schedule.

    Dates from Dec 18 to Jan 6 move to the first Wednesday after Jan 6.
    """
    today = today or date.today()
    start = today + timedelta(days=21)

    if (start.month, start.day) >= (12, 18):
        start = date(start.year + 1, 1, 7)
    elif (start.month, start.day) <= (1, 6):
        start = date(start.year, 1, 7)

    return start + timedelta(days=(2 - start.weekday()) % 7)


def count_daily_flights(
    flights: list[FlightSegment],
) -> dict[tuple[str, str], int]:
    """Count distinct Delta flight numbers per nonstop route."""
    numbers: dict[tuple[str, str], set[str]] = defaultdict(set)

    for flight in flights:
        if flight.operating_carrier != "DL":
            continue
        numbers[(flight.origin, flight.destination)].add(flight.flight_number)

    return {route: len(found) for route, found in numbers.items()}


def build_route_list(
    observed: dict[str, dict[tuple[str, str], int]],
) -> list[dict]:
    """Combine observed departures and add assumed return routes."""
    routes: dict[tuple[str, str], dict] = {}

    for counts in observed.values():
        for (origin, destination), daily in counts.items():
            routes[(origin, destination)] = {
                "origin": origin,
                "destination": destination,
                "daily_flights": daily,
                "source": "observed",
            }

    for (origin, destination), route in list(routes.items()):
        if (destination, origin) not in routes:
            routes[(destination, origin)] = {
                "origin": destination,
                "destination": origin,
                "daily_flights": route["daily_flights"],
                "source": "assumed_return",
            }

    return sorted(
        routes.values(),
        key=lambda r: (r["origin"], r["destination"]),
    )


def load_observed(path: Path) -> dict[str, dict[tuple[str, str], int]]:
    """Read previously observed departures back from an output file."""
    if not path.exists():
        return {}

    data = json.loads(path.read_text())
    observed: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)

    for route in data["routes"]:
        if route["source"] == "observed":
            observed[route["origin"]][
                (route["origin"], route["destination"])
            ] = route["daily_flights"]

    return dict(observed)


def fetch_departures(
    provider: OAGFlightProvider,
    airport: str,
    sample_date: date,
) -> list[FlightSegment]:
    timezone = get_airport_timezone(airport)
    start = datetime.combine(sample_date, time(0, 0), tzinfo=timezone)
    end = datetime.combine(sample_date, time(23, 59), tzinfo=timezone)
    return provider.get_flights(airport, start, end)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--airports", nargs="+", default=DEFAULT_AIRPORTS)
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=default_sample_date(),
        help="Sample day to read (YYYY-MM-DD). Defaults to a Wednesday ~3 weeks out.",
    )
    parser.add_argument("--request-budget", type=int, default=60)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    airports = [code.upper() for code in args.airports]
    provider = OAGFlightProvider(max_requests=args.request_budget)
    observed = load_observed(args.output)

    print(f"Sample date: {args.date} ({args.date:%A})")
    print(f"Request budget: {args.request_budget}")

    for airport in airports:
        before = provider.request_count
        try:
            flights = fetch_departures(provider, airport, args.date)
        except RuntimeError as error:
            print(f"\nStopped at {airport}: {error}")
            print("Nothing was written. Raise --request-budget or run fewer airports.")
            raise SystemExit(1) from error

        counts = count_daily_flights(flights)
        observed[airport] = counts
        print(
            f"{airport}: {len(counts)} routes, {sum(counts.values())} daily flights, "
            f"{provider.request_count - before} requests"
        )

    routes = build_route_list(observed)
    output = {
        "description": (
            "Delta-operated nonstop routes and daily flight counts. "
            "Demo flight times are generated from this list."
        ),
        "airports": sorted(observed),
        "sample_weekday": f"{args.date:%A}",
        "routes": routes,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")

    print(f"\nTotal requests: {provider.request_count}")
    print(f"Wrote {len(routes)} routes to {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
