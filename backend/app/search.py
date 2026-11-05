from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.base import FlightProvider
from backend.app.providers.schedules import collect_traveler_schedules
from backend.app.routing.itineraries import search_meeting_itineraries
from backend.app.ranking.scoring import (
    RankingWeights,
    rank_destinations,
)

def search_meetup_itineraries(
    provider: FlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
):
    """Find feasible meetup itineraries using provider-fetched schedules"""

    flights_a = collect_traveler_schedules(
        provider,
        traveler_a,
        constraints,
    )

    flights_b = collect_traveler_schedules(
        provider,
        traveler_b,
        constraints,
    )

    flights = flights_a + flights_b

    return search_meeting_itineraries(
        flights,
        traveler_a,
        traveler_b,
        constraints,
    )

def search_ranked_meetups(
    provider: FlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
    weights: RankingWeights,
):
    """Find and rank meetup destinations using provider-fetched schedules"""

    pairs = search_meetup_itineraries(
        provider,
        traveler_a,
        traveler_b,
        constraints,
    )

    return rank_destinations(
        pairs,
        weights,
    )