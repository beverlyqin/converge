import json
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi


project_root = Path(__file__).resolve().parents[1]
chunks_path = project_root / "data" / "rag" / "chunks.json"

chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
)

def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())

def reciprocal_rank_fusion(
    bm25_ranking,
    dense_ranking,
    k=60,
):
    scores = {}

    for rank, index in enumerate(bm25_ranking, start=1):
        scores[index] = scores.get(index, 0) + 1 / (k + rank)

    for rank, index in enumerate(dense_ranking, start=1):
        scores[index] = scores.get(index, 0) + 1 / (k + rank)

    ranking = sorted(scores,key=scores.get,reverse=True)

    return ranking, scores

question = (
    "How many Delta Sky Club visits do I get "
    "with an Amex Platinum?"
)


# BM25

tokenized_corpus = [
    tokenize(chunk["content"])
    for chunk in chunks
]

bm25 = BM25Okapi(tokenized_corpus)

bm25_scores = bm25.get_scores(
    tokenize(question)
)

bm25_ranking = sorted(
    range(len(bm25_scores)),
    key=lambda i: bm25_scores[i],
    reverse=True,
)


# Dense retrieval

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

dense_results = vector_store.similarity_search_with_score(
    question,
    k=len(chunks),
)

dense_ranking = [
    document.metadata["chunk_index"]
    for document, _ in dense_results
]


# Hybrid RRF
hybrid_ranking, rrf_scores = reciprocal_rank_fusion(
    bm25_ranking,
    dense_ranking,
)


for rank, index in enumerate(hybrid_ranking[:5], start=1):
    chunk = chunks[index]

    print(f"\n--- Rank {rank} ---")
    print(f"RRF Score: {rrf_scores[index]:.5f}")
    print(f"BM25 Rank: {bm25_ranking.index(index) + 1}")
    print(f"Dense Rank: {dense_ranking.index(index) + 1}")
    print(f"Section: {chunk['metadata'].get('section')}")
    print(chunk["content"])