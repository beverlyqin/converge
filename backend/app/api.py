from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.domain.models import (
    Itinerary,
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.oag import OAGFlightProvider
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import search_ranked_meetups
from backend.app.ranking.explanations import (
    DestinationExplanation,
    explain_destination,
)
from backend.app.ranking.metrics import RankingMetrics

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


@app.post("/meetups/search", response_model=list[MeetupSearchResult])
def search_meetups(request: MeetupSearchRequest) -> list[MeetupSearchResult]:
    provider = OAGFlightProvider()
    ranked = search_ranked_meetups(
        provider,
        request.traveler_a,
        request.traveler_b,
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
