from backend.app.tools.flight_tools import search_meetup_options


def test_search_meetup_options_handles_naive_datetimes():
    result = search_meetup_options.invoke({
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:00",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
        "max_stops": 1,
        "max_arrival_gap_minutes": 120,
    })

    assert len(result["results"]) == 1

    meetup = result["results"][0]

    assert meetup["destination"] == "AUS"
    assert meetup["metrics"]["arrival_gap_minutes"] == 95.0
    assert meetup["itinerary_a"]["segments"][0]["flight_number"] == "DL123"
    assert meetup["itinerary_b"]["segments"][0]["flight_number"] == "DL300"


def test_search_meetup_options_treats_midnight_as_overnight_window():
    result = search_meetup_options.invoke({
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T00:00:00",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
        "max_stops": 1,
        "max_arrival_gap_minutes": 120,
    })

    assert len(result["results"]) == 1
    assert result["results"][0]["destination"] == "AUS"
