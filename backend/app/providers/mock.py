import json
from datetime import datetime
from pathlib import Path

from backend.app.domain.models import FlightSegment
from backend.app.providers.base import FlightProvider


class MockFlightProvider(FlightProvider):
    """Load normalized flight data from the local mock fixture."""

    def __init__(self):
        file_path = Path("backend/data/mock_flights.json")

        with open(file_path, "r") as file:
            data = json.load(file)

        self.flights = [
            FlightSegment(**item)
            for item in data
        ]

    def get_flights(
        self,
        origin: str,
        depart_after: datetime,
        depart_before: datetime,
    ) -> list[FlightSegment]:
        """Return Delta-operated flights in the requested window."""
        return [
            flight
            for flight in self.flights
            if flight.origin == origin
            and flight.operating_carrier == "DL"
            and depart_after <= flight.departure_time <= depart_before
        ]


def load_mock_flights() -> list[FlightSegment]:
    """Load all mock flights for existing tests."""
    return MockFlightProvider().flights