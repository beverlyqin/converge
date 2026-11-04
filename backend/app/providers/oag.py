import os
from datetime import datetime, timezone

import httpx

from backend.app.domain.models import FlightSegment
from backend.app.providers.base import FlightProvider

class OAGFlightProvider(FlightProvider):
    """Retrieve Delta-operated schedules from OAG."""

    BASE_URL = "https://api.oag.com/flight-instances/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OAG_API_KEY")

        if not self.api_key:
            raise ValueError("OAG_API_KEY is not set.")

    def get_flights(
        self,
        origin: str,
        depart_after: datetime,
        depart_before: datetime,
    ) -> list[FlightSegment]:
        params = {
            "DepartureDateTime": (
                f"{depart_after.strftime('%Y-%m-%dT%H:%M')}/"
                f"{depart_before.strftime('%Y-%m-%dT%H:%M')}"
            ),
            "DepartureAirport": origin,
            "CarrierCode": "DL",
            "Codeshare": "Operating",
            "FlightType": "Scheduled",
            "CodeType": "IATA",
            "Limit": 1000,
            "version": "v2",
        }

        headers = {
            "Subscription-Key": self.api_key,
        }

        flights = []
        next_url = self.BASE_URL
        next_params = params

        while next_url:
            response = httpx.get(
                next_url,
                headers=headers,
                params=next_params,
                timeout=30.0,
            )

            response.raise_for_status()

            payload = response.json()

            for item in payload.get("data", []):
                flight = parse_oag_flight(item)

                if flight.operating_carrier == "DL":
                    flights.append(flight)

            next_url = payload.get("paging", {}).get("next")
            next_params = None

        return flights

def parse_oag_flight(data: dict) -> FlightSegment:
    """Convert one OAG flight record into domain model"""
    carrier = data["carrier"]["iata"]
    departure_time = datetime.fromisoformat(
        f'{data["departure"]["date"]["utc"]}T'
        f'{data["departure"]["time"]["utc"]}'
    ).replace(tzinfo=timezone.utc)

    arrival_time = datetime.fromisoformat(
        f'{data["arrival"]["date"]["utc"]}T'
        f'{data["arrival"]["time"]["utc"]}'
    ).replace(tzinfo=timezone.utc)

    return FlightSegment(
        flight_number=f'{carrier}{data["flightNumber"]}',
        operating_carrier=carrier,
        origin=data["departure"]["airport"]["iata"],
        destination=data["arrival"]["airport"]["iata"],
        departure_time=departure_time,
        arrival_time=arrival_time,
    )