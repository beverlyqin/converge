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
    
    @property
    def total_duration(self):
        return self.segments[-1].arrival_time - self.segments[0].departure_time

class TravelerRequest(BaseModel):
    origin: str
    depart_after: datetime
    depart_before: datetime
    return_after: datetime | None = None
    return_before: datetime | None = None

