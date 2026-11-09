from langchain_core.tools import tool
from datetime import datetime

from backend.app.airports.timezones import get_airport_timezone
from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.mock import MockFlightProvider
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import search_ranked_meetups

def parse_local_datetime(
    value: str,
    airport: str,
) -> datetime:
    """Parse a datetime and attach the airport timezone if none is provided."""

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=get_airport_timezone(airport)
        )

    return parsed

@tool
def search_meetup_options(
    origin_a: str,
    depart_after_a: str,
    depart_before_a: str,
    origin_b: str,
    depart_after_b: str,
    depart_before_b: str,
    max_stops: int = 1,
    max_arrival_gap_minutes: int = 120,
) -> dict:
    """Find and rank meeting destinations for two travelers."""

    provider = MockFlightProvider()

    traveler_a = TravelerRequest(
        origin=origin_a,
        depart_after=parse_local_datetime(
            depart_after_a,
            origin_a,
        ),
        depart_before=parse_local_datetime(
            depart_before_a,
            origin_a,
        ),
    )

    traveler_b = TravelerRequest(
        origin=origin_b,
        depart_after=parse_local_datetime(
            depart_after_b,
            origin_b,
        ),
        depart_before=parse_local_datetime(
            depart_before_b,
            origin_b,
        ),
    )

    constraints = SearchConstraints(
        max_stops=max_stops,
        max_arrival_gap_minutes=max_arrival_gap_minutes,
    )

    weights = RankingWeights(
        arrival_sync=0.5,
        stops=0.2,
        travel_time=0.3,
        backup_options=0.0,
    )

    ranked = search_ranked_meetups(
        provider=provider,
        traveler_a=traveler_a,
        traveler_b=traveler_b,
        constraints=constraints,
        weights=weights,
    )

    return {
        "results": [
            {
                "destination": destination,
                "score": total_score,
                "backup_options": backup_count,
                "itinerary_a": scored_pair.itinerary_a.model_dump(
                    mode="json"
                ),
                "itinerary_b": scored_pair.itinerary_b.model_dump(
                    mode="json"
                ),
                "metrics": scored_pair.metrics.model_dump(
                    mode="json"
                ),
            }
            for (
                destination,
                scored_pair,
                backup_count,
                total_score,
            ) in ranked
        ]
    }

