import json
from pathlib import Path 

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

project_root = Path(__file__).resolve().parents[1]
chunks_path = project_root / "data" / "rag" / "chunks.json"

chunks = json.loads(
    chunks_path.read_text(encoding="utf-8")
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

vector_store = InMemoryVectorStore(embeddings)

vector_store.add_documents(documents)

question=(
    "How many Delta Sky Club visits do I get "
    "with an Amex Platinum?"
)

results = vector_store.similarity_search_with_score(
    question, 
    k = 5,
)

for rank, (document, score) in enumerate(results, start=1):
    print(f"\n--- Rank {rank} ---")
    print(f"Score: {score:.3f}")
    print(f"Section: {document.metadata.get('section')}")
    print(document.page_content)