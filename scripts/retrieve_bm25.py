import json
import re
from pathlib import Path 

from rank_bm25 import BM25Okapi

project_root = Path(__file__).resolve().parents[1]
chunks_path = project_root / "data" / "rag" / "chunks.json"

chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
)

def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())

tokenized_corpus = [
    tokenize(chunk["content"])
    for chunk in chunks
]

bm25 = BM25Okapi(tokenized_corpus)

question = (
    "How many Delta Sky Club visits do I get "
    "with an Amex Platinum?"
)

tokenized_question = tokenize(question)

scores = bm25.get_scores(tokenized_question)

ranked_indices = sorted(
    range(len(scores)),
    key=lambda i: scores[i],
    reverse=True,
)


for rank, index in enumerate(ranked_indices[:5], start=1):
    chunk = chunks[index]

    print(f"\n--- Rank {rank} ---")
    print(f"Score: {scores[index]:.3f}")
    print(f"Section: {chunk['metadata'].get('section')}")
    print(chunk["content"])