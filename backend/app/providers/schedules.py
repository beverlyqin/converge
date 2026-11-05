from datetime import timedelta

from backend.app.airports.timezones import get_airport_timezone
from backend.app.domain.models import (
    FlightSegment,
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.base import FlightProvider

DELTA_HUB_AIRPORTS = {
    "ATL",
    "BOS",
    "DTW",
    "LAX",
    "LGA",
    "JFK",
    "MSP",
    "SEA",
    "SLC",
}

def collect_direct_schedules(
    provider: FlightProvider,
    travelers: list[TravelerRequest],
) -> list[FlightSegment]:
    """Fetch required direct-flight schedules once per unique query"""

    flights = []
    seen_queries = set()

    for traveler in travelers:
        query = (
            traveler.origin.upper(),
            traveler.depart_after.isoformat(),
            traveler.depart_before.isoformat(),
        )

        if query in seen_queries:
            continue

        seen_queries.add(query)

        flights.extend(
            provider.get_flights(
                origin=traveler.origin,
                depart_after=traveler.depart_after,
                depart_before=traveler.depart_before,
            )
        )

    return flights

def get_connection_airports(
    first_leg_flights: list[FlightSegment],
) -> set[str]:
    """Return unique airports that may be used for connections"""
    return {
        flight.destination
        for flight in first_leg_flights
    }

def get_connection_window(
    first_leg: FlightSegment,
) -> tuple:
    """Return local departure window for a connecting flight"""

    connection_airport = first_leg.destination
    connection_timezone = get_airport_timezone(
        connection_airport
    )

    local_arrival = first_leg.arrival_time.astimezone(
        connection_timezone
    )

    depart_after = local_arrival + timedelta(minutes=45)
    depart_before = local_arrival + timedelta(hours=4)

    return depart_after, depart_before

def get_connection_search_windows(
    first_leg_flights: list[FlightSegment],
) -> dict[str, list[tuple]]:
    """Group & merge overlapping connection windows by airport"""

    windows_by_airport = {}

    for flight in first_leg_flights:
        airport = flight.destination
        window = get_connection_window(flight)

        if airport not in windows_by_airport:
            windows_by_airport[airport] = []

        windows_by_airport[airport].append(window)

    merged_by_airport = {}

    for airport, windows in windows_by_airport.items():
        windows.sort(key=lambda window: window[0])

        merged_windows = []

        for start, end in windows:
            if not merged_windows:
                merged_windows.append((start, end))
                continue

            previous_start, previous_end = merged_windows[-1]

            if start <= previous_end:
                merged_windows[-1] = (
                    previous_start,
                    max(previous_end, end),
                )
            else:
                merged_windows.append((start, end))

        merged_by_airport[airport] = merged_windows

    return merged_by_airport

def collect_connection_schedules(
    provider: FlightProvider,
    first_leg_flights: list[FlightSegment],
) -> list[FlightSegment]:
    """Fetch connection schedules using merged airport search windows"""

    connection_flights = []

    windows_by_airport = get_connection_search_windows(
        first_leg_flights
    )

    for airport, windows in windows_by_airport.items():
        for depart_after, depart_before in windows:
            connection_flights.extend(
                provider.get_flights(
                    origin=airport,
                    depart_after=depart_after,
                    depart_before=depart_before,
                )
            )

    return connection_flights

def collect_traveler_schedules(
    provider: FlightProvider,
    traveler: TravelerRequest,
    constraints: SearchConstraints,
) -> list[FlightSegment]:
    """Collect the schedules required for one traveler."""

    first_leg_flights = provider.get_flights(
        origin=traveler.origin,
        depart_after=traveler.depart_after,
        depart_before=traveler.depart_before,
    )

    if constraints.max_stops == 0:
        return first_leg_flights

    selected_first_legs = select_connection_first_legs(
        first_leg_flights,
        max_airports=4,
    )

    connection_flights = collect_connection_schedules(
        provider,
        selected_first_legs,
    )

    return first_leg_flights + connection_flights

def select_connection_first_legs(
    first_leg_flights: list[FlightSegment],
    max_airports: int = 4,
) -> list[FlightSegment]:
    """Select a bounded set of first legs into Delta hubs."""

    flight_counts = {}

    for flight in first_leg_flights:
        airport = flight.destination

        if airport not in DELTA_HUB_AIRPORTS:
            continue

        flight_counts[airport] = (
            flight_counts.get(airport, 0) + 1
        )

    ranked_airports = sorted(
        flight_counts,
        key=lambda airport: (
            -flight_counts[airport],
            airport,
        ),
    )

    selected_airports = set(
        ranked_airports[:max_airports]
    )

    return [
        flight
        for flight in first_leg_flights
        if flight.destination in selected_airports
    ]

def get_return_search_window(
    traveler: TravelerRequest,
    destination: str,
) -> tuple:
    """Return the destination local window for return departures"""

    if (
        traveler.return_after is None
        or traveler.return_before is None
    ):
        raise ValueError(
            "Traveler does not have a complete return window."
        )

    destination_timezone = get_airport_timezone(
        destination
    )

    return (
        traveler.return_after.astimezone(
            destination_timezone
        ),
        traveler.return_before.astimezone(
            destination_timezone
        ),
    )