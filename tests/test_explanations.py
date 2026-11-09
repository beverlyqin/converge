from datetime import datetime

from backend.app.domain.models import (
    FlightSegment,
    Itinerary,
)
from backend.app.ranking.explanations import (
    explain_destination,
    format_duration_minutes,
)
from backend.app.ranking.metrics import RankingMetrics
from backend.app.ranking.scoring import ScoredItineraryPair


def make_itinerary(
    flight_number: str,
    origin: str,
    destination: str,
    departure_time: str,
    arrival_time: str,
) -> Itinerary:
    return Itinerary(
        segments=[
            FlightSegment(
                flight_number=flight_number,
                operating_carrier="DL",
                origin=origin,
                destination=destination,
                departure_time=datetime.fromisoformat(departure_time),
                arrival_time=datetime.fromisoformat(arrival_time),
            )
        ]
    )


def test_format_duration_minutes():
    assert format_duration_minutes(45) == "45m"
    assert format_duration_minutes(60) == "1h"
    assert format_duration_minutes(95) == "1h 35m"


def test_explain_destination_uses_raw_itinerary_facts():
    itinerary_a = make_itinerary(
        "DL123",
        "JFK",
        "AUS",
        "2026-11-13T17:30:00-05:00",
        "2026-11-13T20:35:00-06:00",
    )

    itinerary_b = make_itinerary(
        "DL300",
        "SEA",
        "AUS",
        "2026-11-13T16:30:00-08:00",
        "2026-11-13T22:10:00-06:00",
    )

    scored_pair = ScoredItineraryPair(
        itinerary_a=itinerary_a,
        itinerary_b=itinerary_b,
        metrics=RankingMetrics(
            arrival_gap_minutes=95.0,
            total_stops=0,
            total_travel_time_minutes=465.0,
        ),
        arrival_sync_score=1.0,
        stops_score=1.0,
        travel_time_score=1.0,
        total_score=1.0,
    )

    explanation = explain_destination(
        scored_pair,
        backup_count=0,
    )

    assert explanation.reasons == [
        "Both travelers fly nonstop.",
        "Travelers arrive 1h 35m apart.",
        "Travel times are 4h 05m for Traveler A and 3h 40m for Traveler B.",
        (
            "No shared backup itinerary layer is available "
            "in the current result set."
        ),
    ]
