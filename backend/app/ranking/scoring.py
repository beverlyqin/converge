from pydantic import BaseModel, Field, model_validator
from backend.app.domain.models import Itinerary, FlightSegment, TravelerRequest, SearchConstraints
from backend.app.ranking.metrics import RankingMetrics, calculate_ranking_metrics
from backend.app.routing.itineraries import search_meeting_itineraries

class RankingWeights(BaseModel):
    arrival_sync: float = Field(ge=0)
    stops: float = Field(ge=0)
    travel_time: float = Field(ge=0)
    backup_options: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def require_positive_weight(self):
        if (
            self.arrival_sync == 0
            and self.stops == 0
            and self.travel_time == 0
            and self.backup_options == 0
        ):
            raise ValueError(
                "At least one ranking weight must be positive."
            )

        return self

class ScoredItineraryPair(BaseModel):
    itinerary_a: Itinerary
    itinerary_b: Itinerary
    metrics: RankingMetrics
    arrival_sync_score: float
    stops_score: float
    travel_time_score: float
    total_score: float


class DestinationCandidate(BaseModel):
    destination: str
    itinerary_pairs: list[tuple[Itinerary, Itinerary]]


def normalize_lower_is_better(
    values: list[float],
) -> list[float]:
    """normalize values to 0–1, where lower values score higher."""

    minimum = min(values)
    maximum = max(values)

    if minimum == maximum:
        return [1.0] * len(values)

    return [
        1 - ((value - minimum) / (maximum - minimum))
        for value in values
    ]

def score_itinerary_pairs(
    pairs: list[tuple[Itinerary, Itinerary]],
    weights: RankingWeights,
) -> list[ScoredItineraryPair]: 
    """Score and rank valid itinerary paris"""
    if not pairs:
        return []

    metrics_list = [
        calculate_ranking_metrics(
            itinerary_a,
            itinerary_b,
        )
        for itinerary_a, itinerary_b in pairs
    ]
    arrival_gaps = [
        metrics.arrival_gap_minutes
        for metrics in metrics_list
    ]
    stop_counts = [
        metrics.total_stops
        for metrics in metrics_list
    ]
    travel_times = [
        metrics.total_travel_time_minutes
        for metrics in metrics_list
    ]
    # senstive to outliers using min-max normalizations
    arrival_scores = normalize_lower_is_better(arrival_gaps)
    stop_scores = normalize_lower_is_better(stop_counts)
    travel_time_scores = normalize_lower_is_better(travel_times)

    scored_pairs = []
    for i, (itinerary_a, itinerary_b) in enumerate(pairs):
        total_score = (
            arrival_scores[i] * weights.arrival_sync
            + stop_scores[i] * weights.stops
            + travel_time_scores[i] * weights.travel_time
        )
        scored_pair = ScoredItineraryPair(
            itinerary_a=itinerary_a,
            itinerary_b=itinerary_b,
            metrics=metrics_list[i],
            arrival_sync_score=arrival_scores[i],
            stops_score=stop_scores[i],
            travel_time_score=travel_time_scores[i],
            total_score=total_score,
        )

        scored_pairs.append(scored_pair)
    scored_pairs.sort(
        key=lambda pair: pair.total_score,
        reverse=True,
    )

    return scored_pairs

def rank_meeting_itineraries(
    flights: list[FlightSegment],
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest, 
    constraints: SearchConstraints,
    weights: RankingWeights,
) -> list[ScoredItineraryPair]:
    """Find feasible meetup itineraries and rank them"""
    pairs = search_meeting_itineraries(
        flights,
        traveler_a,
        traveler_b,
        constraints,
    )

    return score_itinerary_pairs(
        pairs,
        weights,
    )

def get_itinerary_signature(
    itinerary: Itinerary,
) -> tuple[str, ...]:
    """Identify an itinerary by its sequence of flights."""

    return tuple(
        segment.flight_number
        for segment in itinerary.segments
    )

def group_pairs_by_destination(
    pairs: list[tuple[Itinerary, Itinerary]],
) -> list[DestinationCandidate]:
    """Group itinerary pairs by shared destination"""

    grouped: dict[str, list[tuple[Itinerary, Itinerary]]] = {}

    for pair in pairs:
        destination = pair[0].destination

        if destination not in grouped:
            grouped[destination] = []

        grouped[destination].append(pair)

    return [
        DestinationCandidate(
            destination=destination,
            itinerary_pairs=itinerary_pairs,
        )
        for destination, itinerary_pairs in grouped.items()
    ]

def get_backup_option_count(
    candidate: DestinationCandidate,
) -> int:
    """Return the number of meaningful backup itinerary layers"""

    itineraries_a = {
        get_itinerary_signature(pair[0])
        for pair in candidate.itinerary_pairs
    }

    itineraries_b = {
        get_itinerary_signature(pair[1])
        for pair in candidate.itinerary_pairs
    }

    option_count = min(len(itineraries_a), len(itineraries_b))

    return max(option_count - 1, 0)

def summarize_destinations(
    pairs: list[tuple[Itinerary, Itinerary]],
    weights: RankingWeights,
) -> list[tuple[str, ScoredItineraryPair, int]]:
    """Summarize each destination using its best pair and backup count"""
    scored_pairs = score_itinerary_pairs(
        pairs,
        weights,
    )

    candidates = group_pairs_by_destination(pairs)
    scored_by_destination: dict[str, list[ScoredItineraryPair]] = {}

    for scored_pair in scored_pairs:
        destination = scored_pair.itinerary_a.destination
        if destination not in scored_by_destination:
            scored_by_destination[destination] = []
        scored_by_destination[destination].append(scored_pair)

    summaries = []

    for candidate in candidates:
        best_pair = scored_by_destination[candidate.destination][0]
        backup_count = get_backup_option_count(candidate)

        summaries.append(
            (
                candidate.destination,
                best_pair,
                backup_count,
            )
        )

    return summaries

def normalize_higher_is_better(
    values: list[float],
) -> list[float]:
    """Normalize values to 0–1, where higher values score higher."""

    minimum = min(values)
    maximum = max(values)

    if minimum == maximum:
        return [1.0] * len(values)

    return [
        (value - minimum) / (maximum - minimum)
        for value in values
    ]

def rank_destinations(
    pairs: list[tuple[Itinerary, Itinerary]],
    weights: RankingWeights,
) -> list[tuple[str, ScoredItineraryPair, int, float]]:
    """Rank destinations using best pair quality and backup flexibility."""

    summaries = summarize_destinations(
        pairs,
        weights,
    )

    if not summaries:
        return []

    backup_counts = [
        backup_count
        for _, _, backup_count in summaries
    ]
    backup_scores = normalize_higher_is_better(backup_counts)
    ranked = []
    for i, (destination, best_pair, backup_count) in enumerate(summaries):
        destination_score = (
            best_pair.total_score
            + backup_scores[i] * weights.backup_options
        )
        ranked.append(
            (
                destination,
                best_pair,
                backup_count,
                destination_score,
            )
        )
    ranked.sort(
        key=lambda result: result[3],
        reverse=True,
    )

    return ranked

def rank_meeting_destinations(
    flights: list[FlightSegment],
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
    constraints: SearchConstraints,
    weights: RankingWeights,
) -> list[tuple[str, ScoredItineraryPair, int, float]]:
    """Find feasible meetup options and rank destinations."""

    pairs = search_meeting_itineraries(
        flights,
        traveler_a,
        traveler_b,
        constraints,
    )

    return rank_destinations(
        pairs,
        weights,
    )