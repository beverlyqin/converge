from datetime import timedelta
from backend.app.domain.models import FlightSegment, Itinerary

def get_one_stop_itineraries(
        flights: list[FlightSegment],
        origin: str,
) -> list[Itinerary]:
    itineraries = []
    for first_flight in flights:
        if first_flight.origin != origin:
            continue 
        for second_flight in flights:
            if second_flight.origin != first_flight.destination:
                continue
            layover = second_flight.departure_time - first_flight.arrival_time
            if layover < timedelta(minutes=45) or layover > timedelta(hours=4):
                continue
            itinerary = Itinerary(
                segments=[first_flight, second_flight]
            )
            itineraries.append(itinerary)

    return itineraries