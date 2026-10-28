from backend.app.providers.mock import load_mock_flights
from backend.app.routing.reachability import find_common_destinations

def test_find_common_destinations():
    flights = load_mock_flights()

    result = find_common_destinations(flights, "JFK", "SEA")
    assert result == {"AUS"}