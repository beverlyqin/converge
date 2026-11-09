import os 

from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.domain.models import (
    Itinerary,
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.mock import MockFlightProvider
from backend.app.providers.oag import OAGFlightProvider
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import search_ranked_meetups
from backend.app.ranking.explanations import (
    DestinationExplanation,
    explain_destination,
)
from backend.app.ranking.metrics import RankingMetrics
from backend.app.airports.timezones import get_airport_timezone

app = FastAPI()


class MeetupSearchRequest(BaseModel):
    traveler_a: TravelerRequest
    traveler_b: TravelerRequest
    constraints: SearchConstraints
    weights: RankingWeights

class ComponentScores(BaseModel):
    arrival_sync: float
    stops: float
    travel_time: float


class MeetupSearchResult(BaseModel):
    destination: str
    score: float
    backup_options: int
    itinerary_a: Itinerary
    itinerary_b: Itinerary
    metrics: RankingMetrics
    component_scores: ComponentScores
    explanation: DestinationExplanation

class AgentMeetupRequest(BaseModel):
    question: str


def run_agent(question: str) -> str:
    """Lazy import keeps API startup/tests independent from Gemini initialization."""

    from backend.app.agent.meetup_agent import run_meetup_agent

    return run_meetup_agent(question)

def get_flight_provider():
    if os.getenv("FLIGHT_PROVIDER") == "mock":
        return MockFlightProvider()

    return OAGFlightProvider()

def localize_traveler_request(
    traveler: TravelerRequest,
) -> TravelerRequest:
    timezone = get_airport_timezone(traveler.origin)

    def localize(value):
        if value is None or value.tzinfo is not None:
            return value

        return value.replace(tzinfo=timezone)

    return traveler.model_copy(
        update={
            "depart_after": localize(traveler.depart_after),
            "depart_before": localize(traveler.depart_before),
            "return_after": localize(traveler.return_after),
            "return_before": localize(traveler.return_before),
        }
    )

@app.post("/meetups/search", response_model=list[MeetupSearchResult])
def search_meetups(request: MeetupSearchRequest) -> list[MeetupSearchResult]:
    traveler_a = localize_traveler_request(request.traveler_a)
    traveler_b = localize_traveler_request(request.traveler_b)
    provider = get_flight_provider()
    ranked = search_ranked_meetups(
        provider,
        traveler_a,
        traveler_b,
        request.constraints,
        request.weights,
    )

    return [
        {
            "destination": destination,
            "score": total_score,
            "backup_options": backup_count,
            "itinerary_a": scored_pair.itinerary_a,
            "itinerary_b": scored_pair.itinerary_b,
            "metrics": scored_pair.metrics,
            "component_scores": {
                "arrival_sync": scored_pair.arrival_sync_score,
                "stops": scored_pair.stops_score,
                "travel_time": scored_pair.travel_time_score,
            },
            "explanation": explain_destination(
                scored_pair,
                backup_count,
            ),
        }
        for (
            destination,
            scored_pair,
            backup_count,
            total_score,
        ) in ranked
    ]


@app.post("/agent/meetup")
def agent_meetup(request: AgentMeetupRequest):
    return {
        "answer": run_agent(request.question),
    }
