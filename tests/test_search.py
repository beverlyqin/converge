from backend.app.domain.models import (
    FlightSegment,
    SearchConstraints,
    TravelerRequest,
)
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import (
    search_meetup_itineraries,
    search_ranked_meetups,
    RankingWeights,
    rank_destinations,
)

class FakeFlightProvider:
    def get_flights(
        self,
        origin,
        depart_after,
        depart_before,
    ):
        if origin == "JFK":
            return [
                FlightSegment(
                    flight_number="DL100",
                    operating_carrier="DL",
                    origin="JFK",
                    destination="MIA",
                    departure_time="2026-11-14T03:00:00+00:00",
                    arrival_time="2026-11-14T06:15:00+00:00",
                )
            ]

        if origin == "SEA":
            return [
                FlightSegment(
                    flight_number="DL200",
                    operating_carrier="DL",
                    origin="SEA",
                    destination="ATL",
                    departure_time="2026-11-13T23:00:00+00:00",
                    arrival_time="2026-11-14T03:30:00+00:00",
                )
            ]

        if origin == "ATL":
            return [
                FlightSegment(
                    flight_number="DL300",
                    operating_carrier="DL",
                    origin="ATL",
                    destination="MIA",
                    departure_time="2026-11-14T04:30:00+00:00",
                    arrival_time="2026-11-14T06:20:00+00:00",
                )
            ]

        return []


def test_search_meetup_itineraries_matches_direct_and_one_stop():
    provider = FakeFlightProvider()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T14:00:00-08:00",
        depart_before="2026-11-13T20:00:00-08:00",
    )

    constraints = SearchConstraints(
        max_stops=1,
        max_arrival_gap_minutes=60,
    )

    pairs = search_meetup_itineraries(
        provider,
        traveler_a,
        traveler_b,
        constraints,
    )

    assert len(pairs) == 1

    itinerary_a, itinerary_b = pairs[0]

    assert itinerary_a.destination == "MIA"
    assert itinerary_b.destination == "MIA"

    assert itinerary_a.stops == 0
    assert itinerary_b.stops == 1

    assert [
        segment.flight_number
        for segment in itinerary_b.segments
    ] == [
        "DL200",
        "DL300",
    ]

def test_search_ranked_meetups_returns_ranked_destination():
    provider = FakeFlightProvider()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T14:00:00-08:00",
        depart_before="2026-11-13T20:00:00-08:00",
    )

    constraints = SearchConstraints(
        max_stops=1,
        max_arrival_gap_minutes=60,
    )

    weights = RankingWeights(
        arrival_sync=0.5,
        stops=0.2,
        travel_time=0.3,
        backup_options=0.0,
    )

    ranked = search_ranked_meetups(
        provider,
        traveler_a,
        traveler_b,
        constraints,
        weights,
    )

    assert len(ranked) == 1

    destination, scored_pair, backup_count, total_score = ranked[0]

    assert destination == "MIA"
    assert scored_pair.itinerary_a.stops == 0
    assert scored_pair.itinerary_b.stops == 1
    assert backup_count == 0

def test_reranking_does_not_make_additional_provider_calls():
    class CountingFakeFlightProvider(FakeFlightProvider):
        def __init__(self):
            self.call_count = 0

        def get_flights(
            self,
            origin,
            depart_after,
            depart_before,
        ):
            self.call_count += 1

            return super().get_flights(
                origin,
                depart_after,
                depart_before,
            )

    provider = CountingFakeFlightProvider()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T14:00:00-08:00",
        depart_before="2026-11-13T20:00:00-08:00",
    )

    constraints = SearchConstraints(
        max_stops=1,
        max_arrival_gap_minutes=60,
    )

    pairs = search_meetup_itineraries(
        provider,
        traveler_a,
        traveler_b,
        constraints,
    )

    calls_after_search = provider.call_count

    weights_a = RankingWeights(
        arrival_sync=1.0,
        stops=0.0,
        travel_time=0.0,
        backup_options=0.0,
    )

    weights_b = RankingWeights(
        arrival_sync=0.0,
        stops=1.0,
        travel_time=0.0,
        backup_options=0.0,
    )

    rank_destinations(
        pairs,
        weights_a,
    )

    rank_destinations(
        pairs,
        weights_b,
    )

    assert provider.call_count == calls_after_search