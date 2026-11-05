from backend.app.domain.models import (
    FlightSegment,
    TravelerRequest,
)
from backend.app.providers.schedules import (
    collect_direct_schedules,
    get_connection_airports,
)
from backend.app.providers.schedules import (
    collect_direct_schedules,
    get_connection_airports,
    get_connection_window,
)

class FakeFlightProvider:
    def __init__(self):
        self.call_count = 0

    def get_flights(
        self,
        origin,
        depart_after,
        depart_before,
    ):
        self.call_count += 1

        return [
            FlightSegment(
                flight_number="DL123",
                operating_carrier="DL",
                origin=origin,
                destination="AUS",
                departure_time=depart_after,
                arrival_time=depart_before,
            )
        ]


def test_collect_direct_schedules_deduplicates_queries():
    provider = FakeFlightProvider()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    traveler_b = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    flights = collect_direct_schedules(
        provider,
        [traveler_a, traveler_b],
    )

    assert provider.call_count == 1
    assert len(flights) == 1

def test_get_connection_airports_deduplicates_destinations():
    flights = [
        FlightSegment(
            flight_number="DL100",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T17:00:00-05:00",
            arrival_time="2026-11-13T19:30:00-05:00",
        ),
        FlightSegment(
            flight_number="DL101",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T18:00:00-05:00",
            arrival_time="2026-11-13T20:30:00-05:00",
        ),
        FlightSegment(
            flight_number="DL200",
            operating_carrier="DL",
            origin="JFK",
            destination="DTW",
            departure_time="2026-11-13T17:30:00-05:00",
            arrival_time="2026-11-13T19:45:00-05:00",
        ),
    ]

    airports = get_connection_airports(flights)

    assert airports == {"ATL", "DTW"}

def test_get_connection_window_uses_connection_airport_local_time():
    first_leg = FlightSegment(
        flight_number="DL610",
        operating_carrier="DL",
        origin="JFK",
        destination="ATL",
        departure_time="2026-11-13T22:15:00+00:00",
        arrival_time="2026-11-14T00:45:00+00:00",
    )

    depart_after, depart_before = get_connection_window(
        first_leg
    )

    assert depart_after.isoformat() == "2026-11-13T20:30:00-05:00"
    assert depart_before.isoformat() == "2026-11-13T23:45:00-05:00"