from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings

from backend.app.rag.lounge_retrieval import (
    find_candidate_lounges,
    load_chunks,
    retrieve_policy_for_network,
)


project_root = Path(__file__).resolve().parents[3]
chunks_path = project_root / "data" / "rag" / "chunks.json"


def list_supported_cards() -> list[str]:
    """Return credit cards represented in the lounge-policy chunks."""

    chunks = load_chunks(chunks_path)

    return sorted({
        card
        for chunk in chunks
        if (card := chunk["metadata"].get("card"))
    })


def search_lounge_access(
    card: str,
    airport: str,
) -> dict:
    """Return lounge candidates plus grounded policy evidence."""

    lounge_result = find_lounges.invoke({
        "card": card,
        "airport": airport,
    })

    policies = {}

    for lounge_network in lounge_result["matched_lounge_networks"]:
        policy_result = get_lounge_policy.invoke({
            "card": card,
            "lounge_network": lounge_network,
        })

        policies[lounge_network] = policy_result["evidence"]

    return {
        **lounge_result,
        "policies": policies,
    }


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Load the embedding model only when policy retrieval actually needs it."""

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


@tool
def find_lounges(
    card: str,
    airport: str,
) -> dict:
    """Find lounge candidates for a credit card at an airport."""

    chunks = load_chunks(chunks_path)

    _, lounges = find_candidate_lounges(
        chunks=chunks,
        card=card,
        airport=airport,
    )

    matched_networks = {
        lounge["metadata"]["lounge_network"]
        for lounge in lounges
    }

    return {
        "matched_lounge_networks": sorted(matched_networks),
        "lounges": [
            {
                "name": lounge["metadata"]["source_name"],
                "network": lounge["metadata"]["lounge_network"],
                "airport": lounge["metadata"]["airport"],
                "location": lounge["content"],
            }
            for lounge in lounges
        ],
    }


@tool
def get_lounge_policy(
    card: str,
    lounge_network: str,
) -> dict:
    """Retrieve access-policy evidence for a credit card and lounge network."""

    chunks = load_chunks(chunks_path)

    results = retrieve_policy_for_network(
        chunks=chunks,
        embeddings=get_embeddings(),
        card=card,
        lounge_network=lounge_network,
        k=2,
    )

    return {
        "card": card,
        "lounge_network": lounge_network,
        "evidence": [
            {
                "chunk_id": result.metadata["chunk_id"],
                "content": result.page_content,
            }
            for result in results
        ],
    }
