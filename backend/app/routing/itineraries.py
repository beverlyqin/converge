from datetime import timedelta
from backend.app.domain.models import (
    FlightSegment,
    Itinerary,
    TravelerRequest,
    SearchConstraints,
)
from backend.app.routing.reachability import get_available_flights

def get_one_stop_itineraries(
    flights: list[FlightSegment],
    traveler: TravelerRequest,
) -> list[Itinerary]:
    itineraries = []
    for first_flight in flights:
        if first_flight.origin != traveler.origin:
            continue
        if not (
            traveler.depart_after
            <= first_flight.departure_time
            <= traveler.depart_before
        ):
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

def filter_by_max_stops(
        itineraries: list[Itinerary],
        max_stops: int,
) -> list[Itinerary]:
    return [
        itinerary 
        for itinerary in itineraries 
        if itinerary.stops <= max_stops
    ]

def filter_by_travel_time(
    itineraries: list[Itinerary],
    max_minutes: int,
) -> list[Itinerary]:
    return [
        itinerary
        for itinerary in itineraries
        if itinerary.total_duration.total_seconds() / 60 <= max_minutes
    ]

def get_arrival_gap_minutes(
    itinerary_a: Itinerary,
    itinerary_b: Itinerary,
) -> float:
    arrival_a = itinerary_a.segments[-1].arrival_time
    arrival_b = itinerary_b.segments[-1].arrival_time

    gap = abs(arrival_a - arrival_b)

    return gap.total_seconds() / 60

def filter_by_arrival_sync(
    itinerary_pairs: list[tuple[Itinerary, Itinerary]],
    max_gap_minutes: int,
) -> list[tuple[Itinerary, Itinerary]]:
    return [
        pair
        for pair in itinerary_pairs
        if get_arrival_gap_minutes(pair[0], pair[1]) <= max_gap_minutes
    ]

def get_direct_itineraries(
        flights: list[FlightSegment],
        traveler: TravelerRequest,
) -> list[Itinerary]:
    available_flights = get_available_flights(flights, traveler)
    return[
        Itinerary(segments=[flight])
        for flight in available_flights
    ]

def get_itineraries(
    flights: list[FlightSegment],
    traveler: TravelerRequest,
) -> list[Itinerary]:
    direct = get_direct_itineraries(flights, traveler)
    one_stop = get_one_stop_itineraries(flights, traveler)

    return direct + one_stop

def get_matching_itinerary_pairs(
    itineraries_a: list[Itinerary],
    itineraries_b: list[Itinerary],
) -> list[tuple[Itinerary, Itinerary]]:
    grouped_a = group_itineraries_by_destination(itineraries_a)
    grouped_b = group_itineraries_by_destination(itineraries_b)
    common_destinations = grouped_a.keys() & grouped_b.keys()
    pairs = []

    for destination in common_destinations:
        for itinerary_a in grouped_a[destination]:
            for itinerary_b in grouped_b[destination]:
                pairs.append((itinerary_a, itinerary_b))

    return pairs

def group_itineraries_by_destination(
    itineraries: list[Itinerary],
) -> dict[str, list[Itinerary]]:
    grouped = {}

    for itinerary in itineraries:
        destination = itinerary.destination

        if destination not in grouped:
            grouped[destination] = []

        grouped[destination].append(itinerary)

    return grouped

def apply_itinerary_constraints(
    itineraries: list[Itinerary],
    constraints: SearchConstraints,
) -> list[Itinerary]:
    filtered = filter_by_max_stops(
        itineraries,
        max_stops=constraints.max_stops,
    )
    if constraints.max_travel_time_minutes is not None:
        filtered = filter_by_travel_time(
            filtered,
            max_minutes=constraints.max_travel_time_minutes,
        )

    return filtered