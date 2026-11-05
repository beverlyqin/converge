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