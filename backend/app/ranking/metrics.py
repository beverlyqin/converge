from backend.app.domain.models import Itinerary
from pydantic import BaseModel

class RankingMetrics(BaseModel):
    arrival_gap_minutes: float
    total_stops: int
    total_travel_time_minutes: float

def calculate_ranking_metrics(
        itinerary_a: Itinerary,
        itinerary_b: Itinerary,
) -> RankingMetrics:
    """Calculate raw ranking metrics for a meeting pair"""
    arrival_gap = abs(itinerary_a.segments[-1].arrival_time - itinerary_b.segments[-1].arrival_time)
    total_travel_time = (itinerary_a.total_duration + itinerary_b.total_duration)

    return RankingMetrics(
        arrival_gap_minutes=arrival_gap.total_seconds() / 60,
        total_stops=itinerary_a.stops + itinerary_b.stops,
        total_travel_time_minutes=total_travel_time.total_seconds() / 60,
    )