import json
from datetime import date, datetime, timezone

from backend.app.domain.models import FlightSegment
from scripts.demos.fetch_delta_routes import (
    build_route_list,
    count_daily_flights,
    default_sample_date,
    load_observed,
)


def flight(number, origin, destination, carrier="DL"):
    when = datetime(2026, 12, 16, 12, 0, tzinfo=timezone.utc)
    return FlightSegment(
        flight_number=number,
        operating_carrier=carrier,
        origin=origin,
        destination=destination,
        departure_time=when,
        arrival_time=when,
    )


def test_count_daily_flights_counts_distinct_delta_flight_numbers():
    flights = [
        flight("DL1", "JFK", "ATL"),
        flight("DL1", "JFK", "ATL"),  # duplicate page result
        flight("DL2", "JFK", "ATL"),
        flight("DL3", "JFK", "LAX"),
        flight("AA9", "JFK", "LAX", carrier="AA"),
    ]

    assert count_daily_flights(flights) == {
        ("JFK", "ATL"): 2,
        ("JFK", "LAX"): 1,
    }


def test_build_route_list_adds_assumed_returns_only_when_missing():
    observed = {
        "JFK": {("JFK", "ATL"): 2, ("JFK", "AUS"): 1},
        "ATL": {("ATL", "JFK"): 3},
    }

    routes = {
        (r["origin"], r["destination"]): r
        for r in build_route_list(observed)
    }

    assert routes[("ATL", "JFK")]["daily_flights"] == 3
    assert routes[("ATL", "JFK")]["source"] == "observed"
    assert routes[("AUS", "JFK")] == {
        "origin": "AUS",
        "destination": "JFK",
        "daily_flights": 1,
        "source": "assumed_return",
    }


def test_load_observed_ignores_assumed_returns(tmp_path):
    path = tmp_path / "routes.json"
    path.write_text(json.dumps({"routes": build_route_list({
        "JFK": {("JFK", "AUS"): 1},
    })}))

    assert load_observed(path) == {"JFK": {("JFK", "AUS"): 1}}


def test_default_sample_date_is_a_wednesday_about_three_weeks_out():
    sample = default_sample_date(date(2026, 10, 1))

    assert sample == date(2026, 10, 28)


def test_default_sample_date_skips_the_holiday_schedule():
    assert default_sample_date(date(2026, 11, 28)) == date(2027, 1, 13)
    assert default_sample_date(date(2026, 12, 20)) == date(2027, 1, 13)
