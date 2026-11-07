import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings


project_root = Path(__file__).resolve().parents[1]

chunks_path = project_root / "data" / "rag" / "chunks.json"
eval_path = project_root / "data" / "rag" / "product_eval_queries.json"


chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
)

eval_queries = json.loads(
    eval_path.read_text(encoding="utf-8")
)


documents = [
    Document(
        page_content=chunk["content"],
        metadata=chunk["metadata"],
    )
    for chunk in chunks
]


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)


def retrieve_for_query(query, k):
    card = query.get("card")
    airport = query.get("airport")

    retrieved = []

    if card:
        policy_documents = [
            document
            for document in documents
            if document.metadata.get("card") == card
        ]

        if policy_documents:
            policy_store = InMemoryVectorStore(embeddings)
            policy_store.add_documents(policy_documents)

            policy_results = policy_store.similarity_search(
                query["question"],
                k=k,
            )

            retrieved.extend(policy_results)

    if airport:
        airport_documents = [
            document
            for document in documents
            if document.metadata.get("airport") == airport
        ]

        if airport_documents:
            airport_store = InMemoryVectorStore(embeddings)
            airport_store.add_documents(airport_documents)

            airport_results = airport_store.similarity_search(
                query["question"],
                k=k,
            )

            retrieved.extend(airport_results)

    return retrieved


for k in [1, 2, 3, 5]:
    print(f"\n{'=' * 50}")
    print(f"k = {k}")
    print("=" * 50)

    passed = 0

    for query in eval_queries:
        results = retrieve_for_query(
            query,
            k=k,
        )

        retrieved_ids = {
            document.metadata["chunk_id"]
            for document in results
        }

        required_ids = set(
            query["required_chunk_ids"]
        )

        success = required_ids.issubset(
            retrieved_ids
        )

        if success:
            passed += 1

        print(f"\nQuestion: {query['question']}")
        print(f"PASS: {success}")

        print("Required:")
        for chunk_id in required_ids:
            print(f"  {chunk_id}")

        print("Retrieved:")
        for chunk_id in retrieved_ids:
            print(f"  {chunk_id}")

    accuracy = passed / len(eval_queries)

    print(
        f"\nResult for k={k}: "
        f"{passed}/{len(eval_queries)} "
        f"({accuracy:.1%})"
    )