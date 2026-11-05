import os

import pytest


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
    