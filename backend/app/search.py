from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.base import FlightProvider
from backend.app.providers.schedules import (
    collect_return_schedules,
    collect_traveler_schedules,
)
from backend.app.routing.itineraries import (
    search_meeting_itineraries,
    search_outbound_meeting_itineraries,
)
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
    """Find feasible meetup itineraries using provider-fetched schedules."""

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

    outbound_flights = flights_a + flights_b

    outbound_pairs = search_outbound_meeting_itineraries(
        outbound_flights,
        traveler_a,
        traveler_b,
        constraints,
    )

    if not outbound_pairs:
        return []

    candidate_destinations = {
        itinerary_a.destination
        for itinerary_a, _ in outbound_pairs
    }

    return_flights_a = collect_return_schedules(
        provider,
        traveler_a,
        candidate_destinations,
    )

    return_flights_b = collect_return_schedules(
        provider,
        traveler_b,
        candidate_destinations,
    )

    if not return_flights_a and not return_flights_b:
        return outbound_pairs

    all_flights = (
        outbound_flights
        + return_flights_a
        + return_flights_b
    )

    return search_meeting_itineraries(
        all_flights,
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