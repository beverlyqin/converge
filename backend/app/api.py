import json
import logging
import os
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.app.observability import SearchTelemetry
from backend.app.domain.models import (
    Itinerary,
    SearchConstraints,
    TravelerRequest,
)
from backend.app.providers.mock import MockFlightProvider
from backend.app.providers.oag import OAGFlightProvider, TTLFlightCache
from backend.app.ranking.scoring import RankingWeights
from backend.app.search import search_ranked_meetups_with_returns
from backend.app.ranking.explanations import (
    DestinationExplanation,
    explain_destination,
)
from backend.app.ranking.metrics import RankingMetrics
from backend.app.airports.timezones import get_airport_timezone
from backend.app.routing.reachability import get_return_flights

app = FastAPI()
logger = logging.getLogger("flight_meetup.search")

_oag_flight_cache = TTLFlightCache(
    ttl_seconds=float(
        os.getenv("OAG_CACHE_TTL_SECONDS", "900")
    )
)


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
    return_itinerary_a: Itinerary | None = None
    return_itinerary_b: Itinerary | None = None
    metrics: RankingMetrics
    component_scores: ComponentScores
    explanation: DestinationExplanation

class LoungeSearchRequest(BaseModel):
    card: str
    airport: str


class LoungeLocation(BaseModel):
    name: str
    network: str
    airport: str
    location: str


class LoungePolicyEvidence(BaseModel):
    chunk_id: str
    content: str


class LoungeSearchResult(BaseModel):
    matched_lounge_networks: list[str]
    lounges: list[LoungeLocation]
    policies: dict[str, list[LoungePolicyEvidence]]


class AgentMeetupRequest(BaseModel):
    question: str


def run_agent(question: str) -> str:
    """Lazy import keeps API startup/tests independent from Gemini initialization."""

    from backend.app.agent.meetup_agent import run_meetup_agent

    return run_meetup_agent(question)


def get_supported_lounge_cards() -> list[str]:
    """Lazy import keeps API startup independent from embedding dependencies."""

    from backend.app.tools.lounge_tools import list_supported_cards

    return list_supported_cards()


def get_lounge_access(
    card: str,
    airport: str,
) -> dict:
    """Retrieve grounded lounge locations and access-policy evidence."""

    from backend.app.tools.lounge_tools import search_lounge_access

    return search_lounge_access(
        card=card,
        airport=airport,
    )

def get_flight_provider():
    if os.getenv("FLIGHT_PROVIDER") == "mock":
        return MockFlightProvider()

    return OAGFlightProvider(
        cache=_oag_flight_cache,
    )

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

def get_best_return_itinerary(
    flights,
    traveler: TravelerRequest,
    destination: str,
) -> Itinerary | None:
    matching = get_return_flights(
        flights,
        traveler,
        destination,
    )

    if not matching:
        return None

    best_flight = min(
        matching,
        key=lambda flight: flight.departure_time,
    )

    return Itinerary(segments=[best_flight])


@app.post("/meetups/search", response_model=list[MeetupSearchResult])
def search_meetups(request: MeetupSearchRequest) -> list[MeetupSearchResult]:
    try:
        traveler_a = localize_traveler_request(request.traveler_a)
        traveler_b = localize_traveler_request(request.traveler_b)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    provider = get_flight_provider()
    telemetry = SearchTelemetry()
    started = time.perf_counter()

    (
        ranked,
        return_flights_a,
        return_flights_b,
    ) = search_ranked_meetups_with_returns(
        provider,
        traveler_a,
        traveler_b,
        request.constraints,
        request.weights,
        telemetry,
    )

    latency_ms = (time.perf_counter() - started) * 1000

    logger.info(
        json.dumps(
            {
                "event": "meetup_search_completed",
                "provider": provider.__class__.__name__,
                "origin_a": traveler_a.origin,
                "origin_b": traveler_b.origin,
                "latency_ms": round(latency_ms, 2),
                "provider_requests": getattr(
                    provider,
                    "request_count",
                    0,
                ),
                "cache_hits": getattr(
                    provider,
                    "cache_hit_count",
                    0,
                ),
                "cache_misses": getattr(
                    provider,
                    "cache_miss_count",
                    0,
                ),
                "flights_retrieved": telemetry.flights_retrieved,
                "candidate_destinations": telemetry.candidate_destinations,
                "final_results": telemetry.final_results,
            }
        )
    )

    return [
        {
            "destination": destination,
            "score": total_score,
            "backup_options": backup_count,
            "itinerary_a": scored_pair.itinerary_a,
            "itinerary_b": scored_pair.itinerary_b,
            "return_itinerary_a": get_best_return_itinerary(
                return_flights_a,
                traveler_a,
                destination,
            ),
            "return_itinerary_b": get_best_return_itinerary(
                return_flights_b,
                traveler_b,
                destination,
            ),
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


@app.get("/lounges/cards")
def lounge_cards():
    return {
        "cards": get_supported_lounge_cards(),
    }


@app.post("/lounges/search", response_model=LoungeSearchResult)
def search_lounges(request: LoungeSearchRequest) -> LoungeSearchResult:
    result = get_lounge_access(
        card=request.card,
        airport=request.airport.upper(),
    )

    return LoungeSearchResult(**result)


@app.post("/agent/meetup")
def agent_meetup(request: AgentMeetupRequest):
    return {
        "answer": run_agent(request.question),
    }
