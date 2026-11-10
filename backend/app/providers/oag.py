import os
import time
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import parse_qs, urlparse

import httpx

from backend.app.domain.models import FlightSegment
from backend.app.providers.base import FlightProvider


CacheKey = tuple[str, str, str]


class TTLFlightCache:
    """Small process-local TTL cache for normalized OAG flight results."""

    def __init__(self, ttl_seconds: float = 900.0):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self.ttl_seconds = ttl_seconds
        self._entries: dict[
            CacheKey,
            tuple[float, list[FlightSegment]],
        ] = {}
        self._lock = Lock()

    def get(self, key: CacheKey) -> list[FlightSegment] | None:
        now = time.monotonic()

        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            expires_at, flights = entry

            if expires_at <= now:
                del self._entries[key]
                return None

            return list(flights)

    def set(
        self,
        key: CacheKey,
        flights: list[FlightSegment],
    ) -> None:
        expires_at = time.monotonic() + self.ttl_seconds

        with self._lock:
            self._entries[key] = (
                expires_at,
                list(flights),
            )


class OAGFlightProvider(FlightProvider):
    """Retrieve Delta-operated schedules from OAG."""

    BASE_URL = "https://api.oag.com/flight-instances/"

    def __init__(
        self,
        api_key: str | None = None,
        max_requests: int = 25,
        cache: TTLFlightCache | None = None,
    ):
        self.api_key = api_key or os.getenv("OAG_API_KEY")

        if not self.api_key:
            raise ValueError("OAG_API_KEY is not set.")

        self.max_requests = max_requests
        self.request_count = 0
        self._cache = cache or TTLFlightCache()

    def get_flights(
        self,
        origin: str,
        depart_after: datetime,
        depart_before: datetime,
    ) -> list[FlightSegment]:
        origin = origin.upper()

        cache_key = (
            origin,
            depart_after.isoformat(),
            depart_before.isoformat(),
        )

        cached_flights = self._cache.get(cache_key)

        if cached_flights is not None:
            return cached_flights

        params = {
            "DepartureDateTime": (
                f"{depart_after.strftime('%Y-%m-%dT%H:%M')}/"
                f"{depart_before.strftime('%Y-%m-%dT%H:%M')}"
            ),
            "DepartureAirport": origin,
            "CarrierCode": "DL",
            "Codeshare": "Operating",
            "FlightType": "Scheduled",
            "ServiceType": "J,S",
            "CodeType": "IATA",
            "version": "v2",
        }

        headers = {
            "Subscription-Key": self.api_key,
        }

        flights = []
        after = None

        while True:
            request_params = params.copy()

            if after is not None:
                request_params["After"] = after

            response = None

            for attempt in range(4):
                try:
                    if self.request_count >= self.max_requests:
                        raise RuntimeError(
                            f"OAG request budget exceeded: "
                            f"{self.request_count}/{self.max_requests}"
                        )
                    self.request_count += 1
                    response = httpx.get(
                        self.BASE_URL,
                        headers=headers,
                        params=request_params,
                        timeout=30.0,
                        trust_env=False,
                    )

                    response.raise_for_status()
                    break

                except httpx.HTTPStatusError as error:
                    if error.response.status_code != 429:
                        raise RuntimeError(
                            f"OAG request failed: "
                            f"{error.response.status_code} "
                            f"{error.response.text}"
                        ) from error

                    if attempt == 3:
                        raise RuntimeError(
                            f"OAG rate limit exceeded: "
                            f"{error.response.text}"
                        ) from error

                    retry_after = int(
                        error.response.headers.get(
                            "Retry-After",
                            "5",
                        )
                    )

                    time.sleep(retry_after)

                except (
                    httpx.ConnectError,
                    httpx.RemoteProtocolError,
                    httpx.ReadTimeout,
                ):
                    if attempt == 3:
                        raise

            payload = response.json()

            for item in payload.get("data", []):
                number_of_stops = (
                    item.get("segmentInfo", {})
                    .get("numberOfStops", 0)
                )

                if number_of_stops != 0:
                    continue

                flight = parse_oag_flight(item)

                if flight.operating_carrier == "DL":
                    flights.append(flight)

            next_link = payload.get("paging", {}).get("next")

            if not next_link:
                break

            query = parse_qs(
                urlparse(next_link).query
            )

            after_values = query.get("After")

            if not after_values:
                break

            after = after_values[0]

        self._cache.set(
            cache_key,
            flights,
        )

        return flights

def parse_oag_flight(data: dict) -> FlightSegment:
    """Convert one OAG flight record into domain model"""
    carrier = data["carrier"]["iata"]
    departure_time = datetime.fromisoformat(
        f'{data["departure"]["date"]["utc"]}T'
        f'{data["departure"]["time"]["utc"]}'
    ).replace(tzinfo=timezone.utc)

    arrival_time = datetime.fromisoformat(
        f'{data["arrival"]["date"]["utc"]}T'
        f'{data["arrival"]["time"]["utc"]}'
    ).replace(tzinfo=timezone.utc)

    return FlightSegment(
        flight_number=f'{carrier}{data["flightNumber"]}',
        operating_carrier=carrier,
        origin=data["departure"]["airport"]["iata"],
        destination=data["arrival"]["airport"]["iata"],
        departure_time=departure_time,
        arrival_time=arrival_time,
    )