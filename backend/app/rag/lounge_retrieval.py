import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore


def load_chunks(path: Path) -> list[dict[str, Any]]:
    """Load precomputed lounge-policy/location chunks from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _card_lounge_networks(
    chunks: list[dict[str, Any]],
    card: str,
) -> set[str]:
    """Return lounge networks explicitly associated with a card policy."""

    return {
        chunk["metadata"]["lounge_network"]
        for chunk in chunks
        if (
            chunk["metadata"].get("card") == card
            and chunk["metadata"].get("lounge_network")
        )
    }


def find_candidate_lounges(
    chunks: list[dict[str, Any]],
    card: str,
    airport: str,
) -> tuple[set[str], list[dict[str, Any]]]:
    """Find airport lounge-location chunks whose network is covered by a card."""

    networks = _card_lounge_networks(
        chunks=chunks,
        card=card,
    )

    lounges = [
        chunk
        for chunk in chunks
        if (
            chunk["metadata"].get("document_type") == "lounge_location"
            and chunk["metadata"].get("airport") == airport
            and chunk["metadata"].get("lounge_network") in networks
        )
    ]

    return networks, lounges


def retrieve_policy_for_network(
    chunks: list[dict[str, Any]],
    embeddings,
    card: str,
    lounge_network: str,
    k: int = 2,
) -> list[Document]:
    """Retrieve the most relevant policy chunks for one card/lounge network."""

    policy_documents = [
        Document(
            page_content=chunk["content"],
            metadata=chunk["metadata"],
        )
        for chunk in chunks
        if (
            chunk["metadata"].get("document_type")
            == "credit_card_lounge_policy"
            and chunk["metadata"].get("card") == card
            and chunk["metadata"].get("lounge_network")
            == lounge_network
        )
    ]

    if not policy_documents:
        return []

    store = InMemoryVectorStore(embeddings)
    store.add_documents(policy_documents)

    query = (
        f"What access does {card} provide to the "
        f"{lounge_network}, including important restrictions?"
    )

    return store.similarity_search(
        query,
        k=min(k, len(policy_documents)),
    )
