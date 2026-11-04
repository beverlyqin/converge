from datetime import datetime, timezone

from backend.app.providers.oag import OAGFlightProvider, parse_oag_flight


def test_parse_oag_flight():
    oag_flight = {
        "carrier": {
            "iata": "DL",
        },
        "flightNumber": "123",
        "departure": {
            "airport": {
                "iata": "JFK",
            },
            "date": {
                "utc": "2026-11-13",
            },
            "time": {
                "utc": "22:30:00",
            },
        },
        "arrival": {
            "airport": {
                "iata": "AUS",
            },
            "date": {
                "utc": "2026-11-14",
            },
            "time": {
                "utc": "01:35:00",
            },
        },
    }

    flight = parse_oag_flight(oag_flight)

    assert flight.flight_number == "DL123"
    assert flight.operating_carrier == "DL"
    assert flight.origin == "JFK"
    assert flight.destination == "AUS"

    assert flight.departure_time == datetime(
        2026, 11, 13, 22, 30, tzinfo=timezone.utc
    )

    assert flight.arrival_time == datetime(
        2026, 11, 14, 1, 35, tzinfo=timezone.utc
    )



def test_oag_provider_get_flights(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "carrier": {
                            "iata": "DL",
                        },
                        "flightNumber": "123",
                        "departure": {
                            "airport": {
                                "iata": "JFK",
                            },
                            "date": {
                                "utc": "2026-11-13",
                            },
                            "time": {
                                "utc": "22:30:00",
                            },
                        },
                        "arrival": {
                            "airport": {
                                "iata": "AUS",
                            },
                            "date": {
                                "utc": "2026-11-14",
                            },
                            "time": {
                                "utc": "01:35:00",
                            },
                        },
                    }
                ],
                "paging": {},
            }

    def fake_get(url, headers, params, timeout):
        return FakeResponse()

    monkeypatch.setattr(
        "backend.app.providers.oag.httpx.get",
        fake_get,
    )

    provider = OAGFlightProvider(
        api_key="fake-key"
    )

    flights = provider.get_flights(
        origin="JFK",
        depart_after=datetime(
            2026, 11, 13, 17, 0,
            tzinfo=timezone.utc,
        ),
        depart_before=datetime(
            2026, 11, 13, 23, 59,
            tzinfo=timezone.utc,
        ),
    )

    assert len(flights) == 1
    assert flights[0].flight_number == "DL123"
    assert flights[0].origin == "JFK"
    assert flights[0].destination == "AUS"