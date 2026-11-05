from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.oag import OAGFlightProvider
from backend.app.ranking.scoring import RankingWeights, rank_meeting_destinations
from backend.app.providers.schedules import collect_direct_schedules

def main():
    provider = OAGFlightProvider()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T16:00:00-08:00",
        depart_before="2026-11-13T23:59:00-08:00",
    )
    flights = collect_direct_schedules(
        provider,
        [traveler_a, traveler_b],
    )

    constraints = SearchConstraints(
        max_stops=0,
        max_travel_time_minutes=None,
        max_arrival_gap_minutes=180,
    )

    weights = RankingWeights(
        arrival_sync=0.5,
        stops=0.2,
        travel_time=0.3,
        backup_options=0.0,
    )

    ranked = rank_meeting_destinations(
        flights,
        traveler_a,
        traveler_b,
        constraints,
        weights,
    )
    print(f"Flights collected: {len(flights)}")
    print(f"OAG HTTP requests: {provider.request_count}")
    print(f"Common destinations: {len(ranked)}")
    print(f"Common destinations: {len(ranked)}")
    print()

    for destination, best_pair, backup_count, score in ranked[:10]:
        print(
            destination,
            "| score:",
            round(score, 3),
            "| arrival gap:",
            round(best_pair.metrics.arrival_gap_minutes),
            "min",
            "| total travel:",
            round(best_pair.metrics.total_travel_time_minutes),
            "min",
            "| backups:",
            backup_count,
        )

        print(
            "   A:",
            best_pair.itinerary_a.segments[0].flight_number,
            traveler_a.origin,
            "->",
            destination,
            best_pair.itinerary_a.segments[0].arrival_time,
        )

        print(
            "   B:",
            best_pair.itinerary_b.segments[0].flight_number,
            traveler_b.origin,
            "->",
            destination,
            best_pair.itinerary_b.segments[0].arrival_time,
        )


if __name__ == "__main__":
    main()