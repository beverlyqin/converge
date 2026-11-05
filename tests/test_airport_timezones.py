from backend.app.airports.timezones import get_airport_timezone


def test_get_airport_timezone():
    assert get_airport_timezone("JFK").key == "America/New_York"
    assert get_airport_timezone("ATL").key == "America/New_York"
    assert get_airport_timezone("SEA").key == "America/Los_Angeles"