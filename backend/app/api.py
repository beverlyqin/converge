from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.domain.models import (
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.oag import OAGFlightProvider
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import search_ranked_meetups


app = FastAPI()


class MeetupSearchRequest(BaseModel):
    traveler_a: TravelerRequest
    traveler_b: TravelerRequest
    constraints: SearchConstraints
    weights: RankingWeights


class AgentMeetupRequest(BaseModel):
    question: str


def run_agent(question: str) -> str:
    """Lazy import keeps API startup/tests independent from Gemini initialization."""

    from backend.app.agent.meetup_agent import run_meetup_agent

    return run_meetup_agent(question)


@app.post("/meetups/search")
def search_meetups(request: MeetupSearchRequest):
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
