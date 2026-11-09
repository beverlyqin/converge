from pathlib import Path

from backend.app.rag.lounge_retrieval import (
    find_candidate_lounges,
    load_chunks,
)


CHUNKS_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "rag"
    / "chunks.json"
)


def test_amex_platinum_finds_aus_delta_sky_club():
    chunks = load_chunks(CHUNKS_PATH)

    _, lounges = find_candidate_lounges(
        chunks=chunks,
        card="Amex Platinum",
        airport="AUS",
    )

    names = {
        lounge["metadata"]["source_name"]
        for lounge in lounges
    }

    assert "AUS Delta Sky Club" in names


def test_key_airports_have_lounge_location_coverage():
    chunks = load_chunks(CHUNKS_PATH)

    covered_airports = {
        chunk["metadata"]["airport"]
        for chunk in chunks
        if chunk["metadata"].get("document_type") == "lounge_location"
    }

    assert {"AUS", "ATL", "SEA", "LAX"} <= covered_airports
