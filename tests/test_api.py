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
        lambda **kwargs: FakeFlightProvider(),
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
    assert "explanation" in data[0]
    assert data[0]["explanation"]["reasons"][0] == "Both travelers fly nonstop."


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

def test_meetup_search_openapi_schema():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    response_schema = (
        schema["paths"]["/meetups/search"]["post"]
        ["responses"]["200"]["content"]["application/json"]["schema"]
    )

    assert response_schema["type"] == "array"
    assert response_schema["items"]["$ref"] == (
        "#/components/schemas/MeetupSearchResult"
    )

def test_search_meetups_rejects_unknown_airport():
    client = TestClient(app)

    response = client.post(
        "/meetups/search",
        json={
            "traveler_a": {
                "origin": "XXX",
                "depart_after": "2026-11-13T17:00:00",
                "depart_before": "2026-11-13T23:59:00",
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

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unknown airport timezone: XXX"
    }


def test_search_meetups_returns_round_trip_itineraries(monkeypatch):
    class RoundTripProvider:
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

            if origin == "MIA":
                return [
                    FlightSegment(
                        flight_number="DL300",
                        operating_carrier="DL",
                        origin="MIA",
                        destination="JFK",
                        departure_time="2026-11-15T23:00:00+00:00",
                        arrival_time="2026-11-16T02:00:00+00:00",
                    ),
                    FlightSegment(
                        flight_number="DL400",
                        operating_carrier="DL",
                        origin="MIA",
                        destination="SEA",
                        departure_time="2026-11-15T23:30:00+00:00",
                        arrival_time="2026-11-16T06:00:00+00:00",
                    ),
                ]

            return []

    monkeypatch.setattr(
        "backend.app.api.OAGFlightProvider",
        lambda **kwargs: RoundTripProvider(),
    )

    client = TestClient(app)

    response = client.post(
        "/meetups/search",
        json={
            "traveler_a": {
                "origin": "JFK",
                "depart_after": "2026-11-13T17:00:00-05:00",
                "depart_before": "2026-11-13T23:59:00-05:00",
                "return_after": "2026-11-15T17:00:00-05:00",
                "return_before": "2026-11-15T23:59:00-05:00",
            },
            "traveler_b": {
                "origin": "SEA",
                "depart_after": "2026-11-13T14:00:00-08:00",
                "depart_before": "2026-11-13T20:00:00-08:00",
                "return_after": "2026-11-15T13:00:00-08:00",
                "return_before": "2026-11-15T20:00:00-08:00",
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
    assert data[0]["return_itinerary_a"]["segments"][0]["flight_number"] == "DL300"
    assert data[0]["return_itinerary_b"]["segments"][0]["flight_number"] == "DL400"


def test_round_trip_without_returns_does_not_fall_back_to_outbound(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.OAGFlightProvider",
        lambda **kwargs: FakeFlightProvider(),
    )

    client = TestClient(app)

    response = client.post(
        "/meetups/search",
        json={
            "traveler_a": {
                "origin": "JFK",
                "depart_after": "2026-11-13T17:00:00-05:00",
                "depart_before": "2026-11-13T23:59:00-05:00",
                "return_after": "2026-11-15T17:00:00-05:00",
                "return_before": "2026-11-15T23:59:00-05:00",
            },
            "traveler_b": {
                "origin": "SEA",
                "depart_after": "2026-11-13T14:00:00-08:00",
                "depart_before": "2026-11-13T20:00:00-08:00",
                "return_after": "2026-11-15T13:00:00-08:00",
                "return_before": "2026-11-15T20:00:00-08:00",
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
    assert response.json() == []


def test_lounge_cards_endpoint(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.get_supported_lounge_cards",
        lambda: ["Amex Platinum", "Capital One Venture X"],
    )

    client = TestClient(app)

    response = client.get("/lounges/cards")

    assert response.status_code == 200
    assert response.json() == {
        "cards": ["Amex Platinum", "Capital One Venture X"]
    }


def test_lounge_search_endpoint(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.get_lounge_access",
        lambda card, airport: {
            "matched_lounge_networks": ["Centurion Lounge"],
            "lounges": [
                {
                    "name": "The Centurion Lounge",
                    "network": "Centurion Lounge",
                    "airport": airport,
                    "location": "Near the main terminal.",
                }
            ],
            "policies": {
                "Centurion Lounge": [
                    {
                        "chunk_id": "policy-1",
                        "content": "Cardholder access is subject to the stated policy.",
                    }
                ]
            },
        },
    )

    client = TestClient(app)

    response = client.post(
        "/lounges/search",
        json={
            "card": "Amex Platinum",
            "airport": "aus",
        },
    )

    assert response.status_code == 200
    assert response.json()["lounges"][0]["airport"] == "AUS"
    assert response.json()["matched_lounge_networks"] == [
        "Centurion Lounge"
    ]
    assert (
        response.json()["policies"]["Centurion Lounge"][0]["chunk_id"]
        == "policy-1"
    )
