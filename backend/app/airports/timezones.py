from zoneinfo import ZoneInfo

import airportsdata


_IATA_AIRPORTS = airportsdata.load("IATA")


def get_airport_timezone(
    airport_code: str,
) -> ZoneInfo:
    """Return the IANA timezone for an IATA airport code."""

    airport = _IATA_AIRPORTS.get(
        airport_code.upper()
    )

    if airport is None or not airport.get("tz"):
        raise ValueError(
            f"Unknown airport timezone: {airport_code}"
        )

    return ZoneInfo(
        airport["tz"]
    )