from abc import ABC, abstractmethod
from datetime import datetime

from backend.app.domain.models import FlightSegment


class FlightProvider(ABC):
    """Interface for retrieving normalized flight data."""

    @abstractmethod
    def get_flights(
        self,
        origin: str,
        depart_after: datetime,
        depart_before: datetime,
    ) -> list[FlightSegment]:
        pass