from pydantic import BaseModel

class RankingWeights(BaseModel):
    arrival_sync: float
    stops: float
    travel_time: float

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