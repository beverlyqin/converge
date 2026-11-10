import pytest
from datetime import datetime, timezone

from backend.app.providers.oag import (
    OAGFlightProvider,
    TTLFlightCache,
    parse_oag_flight,
)


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
        status_code = 200
        headers = {}

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
                        "segmentInfo": {
                            "numberOfStops": 0,
                        },
                    }
                ],
                "paging": {},
            }

    def fake_get(url, headers, params, timeout, **kwargs):
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


def test_oag_provider_caches_identical_queries(monkeypatch):
    call_count = 0

    class FakeResponse:
        status_code = 200
        headers = {}

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
                        "segmentInfo": {
                            "numberOfStops": 0,
                        },
                    }
                ],
                "paging": {},
            }

    def fake_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return FakeResponse()

    monkeypatch.setattr(
        "backend.app.providers.oag.httpx.get",
        fake_get,
    )

    provider = OAGFlightProvider(
        api_key="fake-key",
    )

    depart_after = datetime(
        2026, 11, 13, 17, 0,
        tzinfo=timezone.utc,
    )

    depart_before = datetime(
        2026, 11, 13, 23, 59,
        tzinfo=timezone.utc,
    )

    first = provider.get_flights(
        origin="JFK",
        depart_after=depart_after,
        depart_before=depart_before,
    )

    second = provider.get_flights(
        origin="JFK",
        depart_after=depart_after,
        depart_before=depart_before,
    )

    assert first == second
    assert call_count == 1
    assert provider.request_count == 1

def test_oag_provider_enforces_request_budget(monkeypatch):
    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [],
                "paging": {
                    "next": (
                        "https://api.oag.com/flight-instances/"
                        "?After=next-page"
                    )
                },
            }

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "backend.app.providers.oag.httpx.get",
        fake_get,
    )

    provider = OAGFlightProvider(
        api_key="fake-key",
        max_requests=1,
    )

    with pytest.raises(
        RuntimeError,
        match="OAG request budget exceeded",
    ):
        provider.get_flights(
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

    assert provider.request_count == 1


def test_oag_provider_shares_cache_across_instances(monkeypatch):
    call_count = 0

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "carrier": {"iata": "DL"},
                        "flightNumber": "123",
                        "departure": {
                            "airport": {"iata": "JFK"},
                            "date": {"utc": "2026-11-13"},
                            "time": {"utc": "22:30:00"},
                        },
                        "arrival": {
                            "airport": {"iata": "AUS"},
                            "date": {"utc": "2026-11-14"},
                            "time": {"utc": "01:35:00"},
                        },
                        "segmentInfo": {"numberOfStops": 0},
                    }
                ],
                "paging": {},
            }

    def fake_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return FakeResponse()

    monkeypatch.setattr(
        "backend.app.providers.oag.httpx.get",
        fake_get,
    )

    cache = TTLFlightCache(ttl_seconds=60)

    first_provider = OAGFlightProvider(
        api_key="fake-key",
        cache=cache,
    )
    second_provider = OAGFlightProvider(
        api_key="fake-key",
        cache=cache,
    )

    depart_after = datetime(
        2026, 11, 13, 17, 0,
        tzinfo=timezone.utc,
    )
    depart_before = datetime(
        2026, 11, 13, 23, 59,
        tzinfo=timezone.utc,
    )

    first = first_provider.get_flights(
        origin="JFK",
        depart_after=depart_after,
        depart_before=depart_before,
    )
    second = second_provider.get_flights(
        origin="JFK",
        depart_after=depart_after,
        depart_before=depart_before,
    )

    assert first == second
    assert call_count == 1
    assert first_provider.request_count == 1
    assert second_provider.request_count == 0


def test_ttl_flight_cache_expires(monkeypatch):
    current_time = 1000.0

    monkeypatch.setattr(
        "backend.app.providers.oag.time.monotonic",
        lambda: current_time,
    )

    cache = TTLFlightCache(ttl_seconds=10)

    flight = parse_oag_flight(
        {
            "carrier": {"iata": "DL"},
            "flightNumber": "123",
            "departure": {
                "airport": {"iata": "JFK"},
                "date": {"utc": "2026-11-13"},
                "time": {"utc": "22:30:00"},
            },
            "arrival": {
                "airport": {"iata": "AUS"},
                "date": {"utc": "2026-11-14"},
                "time": {"utc": "01:35:00"},
            },
        }
    )

    key = (
        "JFK",
        "2026-11-13T17:00:00+00:00",
        "2026-11-13T23:59:00+00:00",
    )

    cache.set(key, [flight])

    assert cache.get(key) == [flight]

    current_time = 1011.0

    assert cache.get(key) is None
