from datetime import timedelta

from backend.app.airports.timezones import get_airport_timezone
from backend.app.domain.models import (
    FlightSegment,
    TravelerRequest,
)
from backend.app.providers.base import FlightProvider


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