from datetime import datetime

from backend.app.providers.oag import OAGFlightProvider


def main():
    provider = OAGFlightProvider()

    flights = provider.get_flights(
        origin="JFK",
        depart_after=datetime.fromisoformat(
            "2026-11-13T17:00:00-05:00"
        ),
        depart_before=datetime.fromisoformat(
            "2026-11-13T23:59:00-05:00"
        ),
    )

    print(f"Found {len(flights)} Delta-operated flights")

    for flight in flights[:10]:
        print(
            flight.flight_number,
            flight.origin,
            "->",
            flight.destination,
            flight.departure_time,
            "->",
            flight.arrival_time,
        )


if __name__ == "__main__":
    main()