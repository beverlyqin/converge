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
    traveler_a: TravelerRequest,
    traveler_b: TravelerRequest,
) -> set[str]:
    available_a = get_available_flights(flights, traveler_a)
    available_b = get_available_flights(flights, traveler_b)

    destinations_a = {flight.destination for flight in available_a}
    destinations_b = {flight.destination for flight in available_b}

    common_destinations = destinations_a & destinations_b

    return {
        destination
        for destination in common_destinations
        if has_feasible_return(flights, traveler_a, destination)
        and has_feasible_return(flights, traveler_b, destination)
    }

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

def get_return_flights(
    flights: list[FlightSegment],
    traveler: TravelerRequest,
    destination: str,
) -> list[FlightSegment]:
    if traveler.return_after is None or traveler.return_before is None:
        return []
    return [
        flight 
        for flight in flights
        if flight.origin == destination 
        and flight.destination == traveler.origin
        and traveler.return_after <= flight.departure_time <= traveler.return_before
    ]

def has_feasible_return(
    flights: list[FlightSegment],
    traveler: TravelerRequest,
    destination: str,
) -> bool:
    if traveler.return_after is None or traveler.return_before is None:
        return True

    return len(get_return_flights(flights, traveler, destination)) > 0