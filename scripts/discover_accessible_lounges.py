import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI


project_root = Path(__file__).resolve().parents[1]
chunks_path = project_root / "data" / "rag" / "chunks.json"

chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

def retrieve_policy_for_network(
    card: str,
    lounge_network: str,
    k: int = 2,
):
    policy_chunks = [
        chunk
        for chunk in chunks
        if (
            chunk["metadata"].get("card") == card
            and chunk["metadata"].get("lounge_network")
            == lounge_network
        )
    ]

    documents = [
        Document(
            page_content=chunk["content"],
            metadata=chunk["metadata"],
        )
        for chunk in policy_chunks
    ]

    if not documents:
        return []

    store = InMemoryVectorStore(embeddings)
    store.add_documents(documents)

    queries = [
        (
            f"Who is eligible to access {lounge_network} "
            f"with {card}, and what flight or fare restrictions apply?"
        ),
        (
            f"How many visits to {lounge_network} are included "
            f"with {card}, and are there spending thresholds?"
        ),
        (
            f"What documents and entry requirements are needed "
            f"to enter {lounge_network} with {card}?"
        ),
    ]

    results = {}

    for query in queries:
        matches = store.similarity_search(
            query,
            k=k,
        )

        for match in matches:
            chunk_id = match.metadata["chunk_id"]
            results[chunk_id] = match

    return list(results.values())

def find_candidate_lounges(
    card: str,
    airport: str,
):
    # 1. Find lounge networks associated with this card's policy
    card_networks = {
        chunk["metadata"]["lounge_network"]
        for chunk in chunks
        if (
            chunk["metadata"].get("card") == card
            and chunk["metadata"].get("lounge_network")
        )
    }

    # 2. Find physical lounges at the airport
    # belonging to those networks
    lounge_chunks = [
        chunk
        for chunk in chunks
        if (
            chunk["metadata"].get("airport") == airport
            and chunk["metadata"].get("lounge_network")
            in card_networks
        )
    ]

    return card_networks, lounge_chunks


card = "Amex Platinum"
airport = "JFK"

networks, lounges = find_candidate_lounges(
    card=card,
    airport=airport,
)


print("Eligible lounge networks:")

for network in sorted(networks):
    print(f"- {network}")


print(f"\nMatching lounges at {airport}:")

for lounge in lounges:
    print(
        "-",
        lounge["metadata"]["source_name"],
        f"({lounge['metadata']['lounge_network']})",
    )

policy_by_network = {}

for lounge in lounges:
    network = lounge["metadata"]["lounge_network"]

    if network not in policy_by_network:
        policy_by_network[network] = retrieve_policy_for_network(
            card=card,
            lounge_network=network,
            k=2,
        )

print("\nPolicy evidence:")

for network, policy_results in policy_by_network.items():
    print(f"\n=== {network} ===")

    for result in policy_results:
        print(result.metadata["chunk_id"])
        print(result.page_content)
        print()

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
)

lounge_context = "\n\n".join(
    (
        f"Lounge: {lounge['metadata']['source_name']}\n"
        f"Network: {lounge['metadata']['lounge_network']}\n"
        f"Location information:\n{lounge['content']}"
    )
    for lounge in lounges
)

policy_context_parts = []

for network, policy_results in policy_by_network.items():
    evidence = "\n\n".join(
        result.page_content
        for result in policy_results
    )

    policy_context_parts.append(
        f"Network: {network}\n{evidence}"
    )

policy_context = "\n\n".join(
    policy_context_parts
)

question = (
    "I have an Amex Platinum and I am flying Delta from JFK. "
    "What lounges can I use?"
)

prompt = f"""
You are an airport lounge assistant.

Answer the user's question using only the provided context.

Rules:
- Do not invent or infer access rules that are not explicitly supported.
- Preserve the strength of policy language exactly.
  For example, do not change "may be asked" into "must".
- If an access condition is unknown from the context, say that it is unknown.
- Do not say a user definitely has access if an unresolved condition remains.
- Keep the answer concise.

Clearly distinguish:
- lounges the user can access
- conditional access
- important restrictions
- lounge locations

User card:
{card}

Airport:
{airport}

Question:
{question}

Available lounge locations:
{lounge_context}

Card policy evidence:
{policy_context}
"""

response = model.invoke(prompt)

print("\n=== GENERATED ANSWER ===")
print(response.text)