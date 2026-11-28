import json
from datetime import datetime
from pathlib import Path

from backend.app.domain.models import FlightSegment
from backend.app.providers.base import FlightProvider


DEFAULT_FLIGHTS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "mock_flights.json"
)


class MockFlightProvider(FlightProvider):
    """Load normalized flight data from a local JSON file."""

    def __init__(self, file_path: Path | None = None):
        file_path = file_path or DEFAULT_FLIGHTS_PATH

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


def load_mock_flights(file_path: Path | None = None) -> list[FlightSegment]:
    """Load all flights from a mock data file."""
    return MockFlightProvider(file_path).flights