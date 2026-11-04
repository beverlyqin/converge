import pytest
from pydantic import ValidationError
from datetime import datetime
from backend.app.domain.models import TravelerRequest, SearchConstraints, FlightSegment, Itinerary
from backend.app.providers.mock import load_mock_flights
from backend.app.routing.itineraries import search_meeting_itineraries
from backend.app.ranking.metrics import calculate_ranking_metrics
from backend.app.ranking.scoring import normalize_lower_is_better, RankingWeights, score_itinerary_pairs, rank_meeting_itineraries

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

def test_score_itinerary_pairs_changes_with_weights():
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
        arrival_sync=0.2,
        stops=0.0,
        travel_time=0.8,
    )

    scored = score_itinerary_pairs(
        pairs,
        weights,
    )

    assert scored[0].itinerary_a.destination == "DEN"
    assert scored[1].itinerary_a.destination == "AUS"

def test_ranking_weights_reject_negative_values():
    with pytest.raises(ValidationError):
        RankingWeights(
            arrival_sync=-1,
            stops=1,
            travel_time=1,
        )

def test_ranking_weights_require_at_least_one_positive_value():
    with pytest.raises(ValidationError):
        RankingWeights(
            arrival_sync=0,
            stops=0,
            travel_time=0,
        )

def test_rank_meeting_itineraries():
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

    weights = RankingWeights(
        arrival_sync=0.5,
        stops=0.3,
        travel_time=0.2,
    )

    ranked = rank_meeting_itineraries(
        flights,
        traveler_a,
        traveler_b,
        constraints,
        weights,
    )

    assert len(ranked) == 1
    assert ranked[0].itinerary_a.destination == "AUS"
    assert ranked[0].itinerary_b.destination == "AUS"
    assert ranked[0].total_score == 1.0

def test_search_meeting_itineraries_rejects_infeasible_return():
    flights = load_mock_flights()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
        return_after="2026-11-15T18:00:00-06:00",
        return_before="2026-11-15T23:59:00-06:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T16:00:00-08:00",
        depart_before="2026-11-13T23:59:00-08:00",
        return_after="2026-11-15T18:00:00-06:00",
        return_before="2026-11-15T23:59:00-06:00",
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

    assert pairs == []