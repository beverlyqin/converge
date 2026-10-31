from backend.app.providers.mock import load_mock_flights
from backend.app.routing.reachability import find_common_destinations, get_available_flights, get_return_flights
from backend.app.domain.models import FlightSegment, Itinerary, TravelerRequest
from backend.app.routing.itineraries import (
    get_one_stop_itineraries,
    filter_by_max_stops,
    filter_by_travel_time,
    filter_by_arrival_sync,
)

def test_find_common_destinations():
    flights = load_mock_flights()
    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )
    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T16:00:00-08:00",
        depart_before="2026-11-13T23:59:00-08:00",
    )
    result = find_common_destinations(
        flights,
        traveler_a,
        traveler_b,
    )

    assert result == {"AUS"}

def test_get_availble_flights_filters_by_departure_window():
    flights = load_mock_flights()
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T17:45:00-05:00",
    )

    result = get_available_flights(flights, traveler)
    assert len(result) == 2
    flight_numbers = {flight.flight_number for flight in result}
    assert flight_numbers == {"DL123", "DL610"}

def test_traveler_request_can_be_one_way():
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    assert traveler.return_after is None
    assert traveler.return_before is None

def test_get_return_flights_for_round_trip():
    flights = load_mock_flights()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
        return_after="2026-11-15T15:00:00-06:00",
        return_before="2026-11-15T20:00:00-06:00",
    )

    result = get_return_flights(flights, traveler, "AUS")

    assert len(result) == 1
    assert result[0].flight_number == "DL501"

def test_get_return_flights_for_one_way_trip():
    flights = load_mock_flights()

    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    result = get_return_flights(flights, traveler, "AUS")

    assert result == []

def test_common_destination_requires_feasible_return():
    flights = load_mock_flights()

    traveler_a = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
        return_after="2026-11-15T15:00:00-06:00",
        return_before="2026-11-15T20:00:00-06:00",
    )

    traveler_b = TravelerRequest(
        origin="SEA",
        depart_after="2026-11-13T16:00:00-08:00",
        depart_before="2026-11-13T23:59:00-08:00",
        return_after="2026-11-15T15:00:00-06:00",
        return_before="2026-11-15T20:00:00-06:00",
    )

    result = find_common_destinations(
        flights,
        traveler_a,
        traveler_b,
    )

    assert result == {"AUS"}

def test_itinerary_stop_count():
    segment_1 = FlightSegment(
        flight_number="DL111",
        operating_carrier="DL",
        origin="JFK",
        destination="ATL",
        departure_time="2026-11-13T17:00:00-05:00",
        arrival_time="2026-11-13T19:30:00-05:00",
    )
    segment_2 = FlightSegment(
        flight_number="DL222",
        operating_carrier="DL",
        origin="ATL",
        destination="AUS",
        departure_time="2026-11-13T20:30:00-05:00",
        arrival_time="2026-11-13T22:00:00-06:00",
    )

    itinerary = Itinerary(segments=[segment_1, segment_2])

    assert itinerary.stops == 1

def test_get_one_stop_itineraries():
    flights = load_mock_flights()
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    result = get_one_stop_itineraries(flights, traveler)

    assert len(result) == 1
    assert result[0].stops == 1
    assert result[0].segments[0].flight_number == "DL610"
    assert result[0].segments[1].flight_number == "DL611"
    assert result[0].total_duration.total_seconds() == 20400

def test_filter_by_max_stops():
    flights = load_mock_flights()
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    itineraries = get_one_stop_itineraries(flights, traveler)
    result = filter_by_max_stops(itineraries, 0)

    assert result == []

def test_filter_by_travel_time():
    flights = load_mock_flights()
    traveler = TravelerRequest(
        origin="JFK",
        depart_after="2026-11-13T17:00:00-05:00",
        depart_before="2026-11-13T23:59:00-05:00",
    )

    itineraries = get_one_stop_itineraries(flights, traveler)
    result = filter_by_travel_time(itineraries, 300)

    assert result == []

def test_filter_by_arrival_sync():
    flight_a = FlightSegment(
        flight_number="DL700",
        operating_carrier="DL",
        origin="JFK",
        destination="AUS",
        departure_time="2026-11-13T17:00:00-05:00",
        arrival_time="2026-11-13T20:00:00-06:00",
    )
    flight_b = FlightSegment(
        flight_number="DL701",
        operating_carrier="DL",
        origin="SEA",
        destination="AUS",
        departure_time="2026-11-13T16:00:00-08:00",
        arrival_time="2026-11-13T20:30:00-06:00",
    )

    itinerary_a = Itinerary(segments=[flight_a])
    itinerary_b = Itinerary(segments=[flight_b])

    pairs = [(itinerary_a, itinerary_b)]
    result = filter_by_arrival_sync(pairs, 60)

    assert len(result) == 1