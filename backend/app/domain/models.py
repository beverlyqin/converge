from datetime import datetime 
from pydantic import BaseModel 

class FlightSegment(BaseModel):
    flight_number: str
    operating_carrier: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime

class Itinerary(BaseModel):
    segments: list[FlightSegment]

    @property
    def stops(self) -> int:
        return len(self.segments) - 1

class TravelerRequest(BaseModel):
    origin: str
    depart_after: datetime
    depart_before: datetime
    return_after: datetime | None = None
    return_before: datetime | None = None

