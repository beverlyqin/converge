from backend.app.providers.mock import load_mock_flights
from backend.app.routing.reachability import find_common_destinations, get_available_flights, get_return_flights
from backend.app.domain.models import TravelerRequest


def test_find_common_destinations():
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
    result = find_common_destinations(
        flights,
        traveler_a,
        traveler_b,
    )

    assert result == {"AUS"}

def test_get_availble_flights_filters_by_departure_window():
    flights = load_mock_flights()
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T17:45:00-05:00",
    )
    result = get_available_flights(flights, traveler)

    assert len(result) == 1
    assert result[0].flight_number == "DL123"

def test_traveler_request_can_be_one_way():
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    assert traveler.return_after is None
    assert traveler.return_before is None

def test_get_return_flights_for_round_trip():
    flights = load_mock_flights()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
        return_after="2026-11-15T15:00:00-06:00",
        return_before="2026-11-15T20:00:00-06:00",
    )

    result = get_return_flights(flights, traveler, "AUS")

    assert len(result) == 1
    assert result[0].flight_number == "DL501"

def test_get_return_flights_for_one_way_trip():
    flights = load_mock_flights()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    result = get_return_flights(flights, traveler, "AUS")

    assert result == []