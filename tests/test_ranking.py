from backend.app.domain.models import TravelerRequest, SearchConstraints
from backend.app.providers.mock import load_mock_flights
from backend.app.routing.itineraries import search_meeting_itineraries
from backend.app.ranking.metrics import calculate_ranking_metrics


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