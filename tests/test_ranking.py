from datetime import datetime
from backend.app.domain.models import TravelerRequest, SearchConstraints, FlightSegment, Itinerary
from backend.app.providers.mock import load_mock_flights
from backend.app.routing.itineraries import search_meeting_itineraries
from backend.app.ranking.metrics import calculate_ranking_metrics
from backend.app.ranking.scoring import normalize_lower_is_better, RankingWeights, score_itinerary_pairs

def test_calculate_ranking_metrics():
    flights = load_mock_flights()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )
    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T16:00:00-08:00",
        depart_before="2026-11-13T23:59:00-08:00",
    )
    constraints = SearchConstraints(
        max_stops=0,
        max_travel_time_minutes=300,
        max_arrival_gap_minutes=120,
    )
    pairs = search_meeting_itineraries(
        flights,
        traveler_a,
        traveler_b,
        constraints,
    )
    metrics = calculate_ranking_metrics(
        pairs[0][0],
        pairs[0][1],
    )

    assert metrics.arrival_gap_minutes == 95.0
    assert metrics.total_stops == 0
    assert metrics.total_travel_time_minutes == 465.0

def test_normalize_lower_is_better():
    result = normalize_lower_is_better([20, 60, 100])

    assert result == [1.0, 0.5, 0.0]


def test_normalize_lower_is_better_equal_values():
    result = normalize_lower_is_better([0, 0, 0])

    assert result == [1.0, 1.0, 1.0]

def make_direct_itinerary(
    flight_number: str,
    origin: str,
    destination: str,
    departure_time: str,
    arrival_time: str,
) -> Itinerary:
    """Create a direct itinerary for ranking tests."""

    segment = FlightSegment(
        flight_number=flight_number,
        operating_carrier="DL",
        origin=origin,
        destination=destination,
        departure_time=datetime.fromisoformat(departure_time),
        arrival_time=datetime.fromisoformat(arrival_time),
    )

    return Itinerary(segments=[segment])

def test_score_itinerary_pairs_ranks_by_weights():
    aus_a = make_direct_itinerary(
        "DL101",
        "JFK",
        "AUS",
        "2026-11-13T17:00:00+00:00",
        "2026-11-13T20:00:00+00:00",
    )

    aus_b = make_direct_itinerary(
        "DL102",
        "SEA",
        "AUS",
        "2026-11-13T17:30:00+00:00",
        "2026-11-13T20:15:00+00:00",
    )

    den_a = make_direct_itinerary(
        "DL201",
        "JFK",
        "DEN",
        "2026-11-13T17:00:00+00:00",
        "2026-11-13T19:00:00+00:00",
    )

    den_b = make_direct_itinerary(
        "DL202",
        "SEA",
        "DEN",
        "2026-11-13T17:00:00+00:00",
        "2026-11-13T19:45:00+00:00",
    )
    pairs = [
        (aus_a, aus_b),
        (den_a, den_b),
    ]
    weights = RankingWeights(
        arrival_sync=0.8,
        stops=0.0,
        travel_time=0.2,
    )
    scored = score_itinerary_pairs(
        pairs,
        weights,
    )

    assert scored[0].itinerary_a.destination == "AUS"
    assert scored[1].itinerary_a.destination == "DEN"