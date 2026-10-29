from backend.app.domain.models import FlightSegment, TravelerRequest

def get_direct_destinations(
        flights: list[FlightSegment],
        origin: str,
) -> set[str]:
    return {
        flight.destination
        for flight in flights
        if flight.origin == origin
    }

def find_common_destinations(
    flights: list[FlightSegment],
    origin_a: str,
    origin_b: str,
) -> set[str]:
    destinations_a = get_direct_destinations(flights, origin_a)
    destinations_b = get_direct_destinations(flights, origin_b)

    return destinations_a & destinations_b

def get_available_flights(
    flights: list[FlightSegment],
    traveler: TravelerRequest,
) -> list[FlightSegment]:
    return [
        flight 
        for flight in flights
        if flight.origin == traveler.origin
        and traveler.depart_after <= flight.departure_time <= traveler.depart_before
    ] 