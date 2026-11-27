import os
from pathlib import Path

import pytest

TEST_FLIGHTS_PATH = Path(__file__).parent / "fixtures" / "mock_flights.json"


@pytest.fixture(autouse=True)
def use_test_flight_fixture(monkeypatch):
    """Keep tests on fixed test flights, separate from the demo data."""

    monkeypatch.setattr(
        "backend.app.providers.mock.DEFAULT_FLIGHTS_PATH",
        TEST_FLIGHTS_PATH,
    )


@pytest.fixture(autouse=True)
def block_live_oag_requests(monkeypatch):
    """Prevent accidental live OAG calls during normal tests."""

    if os.getenv("RUN_LIVE_OAG_TESTS") == "1":
        return

    def blocked_get(*args, **kwargs):
        raise RuntimeError(
            "Live OAG requests are disabled during tests."
        )

    monkeypatch.setattr(
        "backend.app.providers.oag.httpx.get",
        blocked_get,
    )
    