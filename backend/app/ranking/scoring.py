from pydantic import BaseModel
from backend.app.domain.models import Itinerary
from backend.app.ranking.metrics import RankingMetrics, calculate_ranking_metrics

class RankingWeights(BaseModel):
    arrival_sync: float
    stops: float
    travel_time: float

class ScoredItineraryPair(BaseModel):
    itinerary_a: Itinerary
    itinerary_b: Itinerary
    metrics: RankingMetrics
    arrival_sync_score: float
    stops_score: float
    travel_time_score: float
    total_score: float

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