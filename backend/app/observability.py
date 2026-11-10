from dataclasses import dataclass


@dataclass
class SearchTelemetry:
    """Counts collected while one meetup search is executed."""

    flights_retrieved: int = 0
    candidate_destinations: int = 0
    final_results: int = 0
