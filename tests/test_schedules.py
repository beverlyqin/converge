from backend.app.domain.models import (
    FlightSegment,
    TravelerRequest,
    SearchConstraints
)
from backend.app.providers.schedules import (
    collect_connection_schedules,
    collect_direct_schedules,
    collect_traveler_schedules,
    get_connection_airports,
    get_connection_search_windows,
    get_connection_window,
    select_connection_first_legs,
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

def test_get_connection_search_windows_merges_overlapping_windows():
    flights = [
        FlightSegment(
            flight_number="DL610",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T22:15:00+00:00",
            arrival_time="2026-11-14T00:45:00+00:00",
        ),
        FlightSegment(
            flight_number="DL620",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T22:45:00+00:00",
            arrival_time="2026-11-14T01:15:00+00:00",
        ),
    ]

    windows = get_connection_search_windows(flights)

    atl_windows = windows["ATL"]

    assert len(atl_windows) == 1

    start, end = atl_windows[0]

    assert start.isoformat() == "2026-11-13T20:30:00-05:00"
    assert end.isoformat() == "2026-11-14T00:15:00-05:00"

def test_get_connection_search_windows_keeps_non_overlapping_windows_separate():
    flights = [
        FlightSegment(
            flight_number="DL610",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T12:00:00+00:00",
            arrival_time="2026-11-13T14:00:00+00:00",
        ),
        FlightSegment(
            flight_number="DL620",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T22:00:00+00:00",
            arrival_time="2026-11-14T00:00:00+00:00",
        ),
    ]

    windows = get_connection_search_windows(flights)

    atl_windows = windows["ATL"]

    assert len(atl_windows) == 2

    first_start, first_end = atl_windows[0]
    second_start, second_end = atl_windows[1]

    assert first_start.isoformat() == "2026-11-13T09:45:00-05:00"
    assert first_end.isoformat() == "2026-11-13T13:00:00-05:00"

    assert second_start.isoformat() == "2026-11-13T19:45:00-05:00"
    assert second_end.isoformat() == "2026-11-13T23:00:00-05:00"

def test_collect_connection_schedules_uses_merged_windows():
    class FakeFlightProvider:
        def __init__(self):
            self.calls = []

        def get_flights(
            self,
            origin,
            depart_after,
            depart_before,
        ):
            self.calls.append(
                (origin, depart_after, depart_before)
            )
            return []

    provider = FakeFlightProvider()

    first_leg_flights = [
        FlightSegment(
            flight_number="DL610",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T22:15:00+00:00",
            arrival_time="2026-11-14T00:45:00+00:00",
        ),
        FlightSegment(
            flight_number="DL620",
            operating_carrier="DL",
            origin="JFK",
            destination="ATL",
            departure_time="2026-11-13T22:45:00+00:00",
            arrival_time="2026-11-14T01:15:00+00:00",
        ),
    ]

    collect_connection_schedules(
        provider,
        first_leg_flights,
    )

    assert len(provider.calls) == 1

    origin, depart_after, depart_before = provider.calls[0]

    assert origin == "ATL"
    assert depart_after.isoformat() == "2026-11-13T20:30:00-05:00"
    assert depart_before.isoformat() == "2026-11-14T00:15:00-05:00"

def test_collect_traveler_schedules_direct_only_makes_one_provider_call():
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

    provider = FakeFlightProvider()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    constraints = SearchConstraints(
        max_stops=0,
    )

    flights = collect_traveler_schedules(
        provider,
        traveler,
        constraints,
    )

    assert provider.call_count == 1
    assert len(flights) == 1

def test_select_connection_first_legs_limits_airports():
    flights = []

    destinations = [
        "ATL",
        "ATL",
        "ATL",
        "DTW",
        "DTW",
        "MSP",
        "MSP",
        "SLC",
        "BOS",
        "AUS",
    ]

    for index, destination in enumerate(destinations):
        flights.append(
            FlightSegment(
                flight_number=f"DL{100 + index}",
                operating_carrier="DL",
                origin="JFK",
                destination=destination,
                departure_time="2026-11-13T22:00:00+00:00",
                arrival_time="2026-11-14T00:00:00+00:00",
            )
        )

    selected = select_connection_first_legs(
        flights,
        max_airports=3,
    )

    selected_airports = {
        flight.destination
        for flight in selected
    }

    assert selected_airports == {
        "ATL",
        "DTW",
        "MSP",
    }

def test_collect_traveler_schedules_fetches_bounded_connections():
    class FakeFlightProvider:
        def __init__(self):
            self.calls = []

        def get_flights(
            self,
            origin,
            depart_after,
            depart_before,
        ):
            self.calls.append(origin)

            if origin == "JFK":
                return [
                    FlightSegment(
                        flight_number="DL100",
                        operating_carrier="DL",
                        origin="JFK",
                        destination="ATL",
                        departure_time="2026-11-13T22:00:00+00:00",
                        arrival_time="2026-11-14T00:30:00+00:00",
                    ),
                    FlightSegment(
                        flight_number="DL101",
                        operating_carrier="DL",
                        origin="JFK",
                        destination="ATL",
                        departure_time="2026-11-13T22:30:00+00:00",
                        arrival_time="2026-11-14T01:00:00+00:00",
                    ),
                ]

            if origin == "ATL":
                return [
                    FlightSegment(
                        flight_number="DL200",
                        operating_carrier="DL",
                        origin="ATL",
                        destination="MIA",
                        departure_time="2026-11-13T21:30:00-05:00",
                        arrival_time="2026-11-13T23:20:00-05:00",
                    )
                ]

            return []

    provider = FakeFlightProvider()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    constraints = SearchConstraints(
        max_stops=1,
    )

    flights = collect_traveler_schedules(
        provider,
        traveler,
        constraints,
    )

    assert provider.calls == [
        "JFK",
        "ATL",
    ]

    assert len(flights) == 3