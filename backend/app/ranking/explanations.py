from pydantic import BaseModel

from backend.app.ranking.scoring import ScoredItineraryPair


class DestinationExplanation(BaseModel):
    reasons: list[str]


def format_duration_minutes(total_minutes: float) -> str:
    """Format minutes as a compact human-readable duration."""

    rounded_minutes = round(total_minutes)
    hours, minutes = divmod(rounded_minutes, 60)

    if hours == 0:
        return f"{minutes}m"

    if minutes == 0:
        return f"{hours}h"

    return f"{hours}h {minutes:02d}m"


def explain_destination(
    scored_pair: ScoredItineraryPair,
    backup_count: int,
) -> DestinationExplanation:
    """Build deterministic user-facing reasons from raw itinerary facts."""

    itinerary_a = scored_pair.itinerary_a
    itinerary_b = scored_pair.itinerary_b

    reasons = []

    if itinerary_a.stops == 0 and itinerary_b.stops == 0:
        reasons.append("Both travelers fly nonstop.")
    else:
        reasons.append(
            "Traveler A has "
            f"{itinerary_a.stops} stop(s); "
            "Traveler B has "
            f"{itinerary_b.stops} stop(s)."
        )

    reasons.append(
        "Travelers arrive "
        f"{format_duration_minutes(scored_pair.metrics.arrival_gap_minutes)} "
        "apart."
    )

    duration_a = itinerary_a.total_duration.total_seconds() / 60
    duration_b = itinerary_b.total_duration.total_seconds() / 60

    reasons.append(
        "Travel times are "
        f"{format_duration_minutes(duration_a)} for Traveler A and "
        f"{format_duration_minutes(duration_b)} for Traveler B."
    )

    if backup_count == 0:
        reasons.append(
            "No shared backup itinerary layer is available "
            "in the current result set."
        )
    elif backup_count == 1:
        reasons.append(
            "1 shared backup itinerary layer is available "
            "for both travelers."
        )
    else:
        reasons.append(
            f"{backup_count} shared backup itinerary layers are available "
            "for both travelers."
        )

    return DestinationExplanation(
        reasons=reasons,
    )
