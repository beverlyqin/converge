from backend.app.providers.mock import load_mock_flights
from backend.app.routing.reachability import find_common_destinations, get_available_flights
from backend.app.domain.models import TravelerRequest


def test_find_common_destinations():
    flights = load_mock_flights()
    result = find_common_destinations(flights, "JFK", "SEA")
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