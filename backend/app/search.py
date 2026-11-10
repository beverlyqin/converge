from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.base import FlightProvider
from backend.app.observability import SearchTelemetry
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

def search_meetup_itineraries_with_returns(
    provider: FlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
    telemetry: SearchTelemetry | None = None,
):
    """Find meetup pairs and retain fetched return schedules for reuse."""

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

    if telemetry is not None:
        telemetry.flights_retrieved += len(outbound_flights)

    outbound_pairs = search_outbound_meeting_itineraries(
        outbound_flights,
        traveler_a,
        traveler_b,
        constraints,
    )

    if not outbound_pairs:
        if telemetry is not None:
            telemetry.candidate_destinations = 0
            telemetry.final_results = 0
        return [], [], []

    candidate_destinations = {
        itinerary_a.destination
        for itinerary_a, _ in outbound_pairs
    }

    if telemetry is not None:
        telemetry.candidate_destinations = len(candidate_destinations)

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

    all_flights = (
        outbound_flights
        + return_flights_a
        + return_flights_b
    )

    if telemetry is not None:
        telemetry.flights_retrieved += (
            len(return_flights_a)
            + len(return_flights_b)
        )

    pairs = search_meeting_itineraries(
        all_flights,
        traveler_a,
        traveler_b,
        constraints,
    )

    return pairs, return_flights_a, return_flights_b


def search_meetup_itineraries(
    provider: FlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
):
    """Find feasible meetup itineraries using provider-fetched schedules."""

    pairs, _, _ = search_meetup_itineraries_with_returns(
        provider,
        traveler_a,
        traveler_b,
        constraints,
    )

    return pairs

def search_ranked_meetups_with_returns(
    provider: FlightProvider,
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
    weights: RankingWeights,
    telemetry: SearchTelemetry | None = None,
):
    """Rank meetup destinations and retain return schedules for the API."""

    pairs, return_flights_a, return_flights_b = (
        search_meetup_itineraries_with_returns(
            provider,
            traveler_a,
            traveler_b,
            constraints,
            telemetry,
        )
    )

    ranked = rank_destinations(
        pairs,
        weights,
    )

    if telemetry is not None:
        telemetry.final_results = len(ranked)

    return (
        ranked,
        return_flights_a,
        return_flights_b,
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