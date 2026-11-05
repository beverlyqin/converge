import json
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi


project_root = Path(__file__).resolve().parents[1]

chunks_path = project_root / "data" / "rag" / "chunks.json"
eval_path = project_root / "data" / "rag" / "eval_queries.json"

chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
)

eval_queries = json.loads(
    eval_path.read_text(encoding="utf-8")
)


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def reciprocal_rank_fusion(
    bm25_ranking,
    dense_ranking,
    k=60,
    bm25_weight=0.3,
    dense_weight=0.7,
):
    scores = {}

    for rank, index in enumerate(bm25_ranking, start=1):
        scores[index] = (
            scores.get(index, 0)
            + bm25_weight / (k + rank)
        )

    for rank, index in enumerate(dense_ranking, start=1):
        scores[index] = (
            scores.get(index, 0)
            + dense_weight / (k + rank)
        )

    return sorted(
        scores,
        key=scores.get,
        reverse=True,
    )


def hit_at_k(ranking, relevant_indices, k):
    return int(
        any(index in relevant_indices for index in ranking[:k])
    )


def reciprocal_rank(ranking, relevant_indices):
    for rank, index in enumerate(ranking, start=1):
        if index in relevant_indices:
            return 1 / rank

    return 0.0


chunk_id_to_index = {
    chunk["metadata"]["chunk_id"]: i
    for i, chunk in enumerate(chunks)
}


# BM25 index

tokenized_corpus = [
    tokenize(chunk["content"])
    for chunk in chunks
]

bm25 = BM25Okapi(tokenized_corpus)


# Dense index

documents = [
    Document(
        page_content=chunk["content"],
        metadata={
            **chunk["metadata"],
            "chunk_index": i,
        },
    )
    for i, chunk in enumerate(chunks)
]

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(documents)


results = {
    "bm25": {
        "hit@1": [],
        "hit@3": [],
        "mrr": [],
    },
    "dense": {
        "hit@1": [],
        "hit@3": [],
        "mrr": [],
    },
    "hybrid": {
        "hit@1": [],
        "hit@3": [],
        "mrr": [],
    },
}


for item in eval_queries:
    question = item["question"]

    relevant_indices = {
        chunk_id_to_index[chunk_id]
        for chunk_id in item["relevant_chunk_ids"]
    }

    # BM25

    bm25_scores = bm25.get_scores(
        tokenize(question)
    )

    bm25_ranking = sorted(
        range(len(chunks)),
        key=lambda i: bm25_scores[i],
        reverse=True,
    )

    # Dense

    dense_results = vector_store.similarity_search(
        question,
        k=len(chunks),
    )

    dense_ranking = [
        document.metadata["chunk_index"]
        for document in dense_results
    ]

    # Hybrid

    hybrid_ranking = reciprocal_rank_fusion(
        bm25_ranking,
        dense_ranking,
    )

    rankings = {
        "bm25": bm25_ranking,
        "dense": dense_ranking,
        "hybrid": hybrid_ranking,
    }

    print(f"\nQuestion: {question}")

    for name, ranking in rankings.items():
        first_relevant_rank = next(
            (
                rank
                for rank, index in enumerate(ranking, start=1)
                if index in relevant_indices
            ),
            None,
        )

        results[name]["hit@1"].append(
            hit_at_k(ranking, relevant_indices, 1)
        )

        results[name]["hit@3"].append(
            hit_at_k(ranking, relevant_indices, 3)
        )

        results[name]["mrr"].append(
            reciprocal_rank(ranking, relevant_indices)
        )

        print(
            f"{name:>6}: "
            f"first relevant rank = {first_relevant_rank}"
        )


print("\n=== Overall Results ===")

for name, metrics in results.items():
    hit1 = sum(metrics["hit@1"]) / len(eval_queries)
    hit3 = sum(metrics["hit@3"]) / len(eval_queries)
    mrr = sum(metrics["mrr"]) / len(eval_queries)

    print(f"\n{name.upper()}")
    print(f"Hit@1: {hit1:.3f}")
    print(f"Hit@3: {hit3:.3f}")
    print(f"MRR:   {mrr:.3f}")