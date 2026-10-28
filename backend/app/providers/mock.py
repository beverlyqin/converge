import json
from pathlib import Path

from backend.app.domain.models import FlightSegment


def load_mock_flights():
    file_path = Path("backend/data/mock_flights.json")

    with open(file_path, "r") as file:
        data = json.load(file)

    flights = [FlightSegment(**item) for item in data]

    return flights