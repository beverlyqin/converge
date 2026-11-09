from fastapi.testclient import TestClient
 
from backend.app.api import app
from backend.app.domain.models import FlightSegment 

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
                    destination="MIA",
                    departure_time="2026-11-13T23:00:00+00:00",
                    arrival_time="2026-11-14T06:20:00+00:00",
                )
            ]

        return []


def test_search_meetups_endpoint(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.OAGFlightProvider",
        lambda: FakeFlightProvider(),
    )

    client = TestClient(app)

    response = client.post(
        "/meetups/search",
        json={
            "traveler_a": {
                "origin": "JFK",
                "depart_after": "2026-11-13T17:00:00-05:00",
                "depart_before": "2026-11-13T23:59:00-05:00",
            },
            "traveler_b": {
                "origin": "SEA",
                "depart_after": "2026-11-13T14:00:00-08:00",
                "depart_before": "2026-11-13T20:00:00-08:00",
            },
            "constraints": {
                "max_stops": 0,
                "max_arrival_gap_minutes": 60,
            },
            "weights": {
                "arrival_sync": 0.5,
                "stops": 0.2,
                "travel_time": 0.3,
                "backup_options": 0.0,
            },
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["destination"] == "MIA"
    assert len(data[0]["itinerary_a"]["segments"]) == 1
    assert len(data[0]["itinerary_b"]["segments"]) == 1 
    assert "metrics" in data[0]
    assert "component_scores" in data[0]


def test_agent_meetup_endpoint(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.run_agent",
        lambda question: f"agent answer for: {question}",
    )

    client = TestClient(app)

    response = client.post(
        "/agent/meetup",
        json={
            "question": (
                "Find a meetup destination for JFK and SEA "
                "and tell me about JFK lounges."
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "agent answer for: Find a meetup destination for JFK and SEA "
            "and tell me about JFK lounges."
        )
    }
