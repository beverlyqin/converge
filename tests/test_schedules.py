from backend.app.domain.models import (
    FlightSegment,
    TravelerRequest,
)
from backend.app.providers.schedules import collect_direct_schedules


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