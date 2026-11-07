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


card = "Amex Platinum"
airport = "JFK"


policy_documents = [
    document
    for document in documents
    if document.metadata.get("card") == card
]

airport_documents = [
    document
    for document in documents
    if document.metadata.get("airport") == airport
]


policy_store = InMemoryVectorStore(embeddings)
policy_store.add_documents(policy_documents)

airport_store = InMemoryVectorStore(embeddings)
airport_store.add_documents(airport_documents)


policy_results = policy_store.similarity_search(
    "What Centurion Lounge access does this card provide?",
    k=3,
)

airport_results = airport_store.similarity_search(
    "Where is the Centurion Lounge and what are its hours?",
    k=3,
)
policy_context = "\n\n".join(
    document.page_content
    for document in policy_results
)

airport_context = "\n\n".join(
    document.page_content
    for document in airport_results
)

prompt = f"""
You are an airport lounge assistant.

Answer the user's question using only the provided context.
Do not invent lounge access rules, locations, or hours.

User has:
Card: {card}
Airport: {airport}

Card policy context:
{policy_context}

Airport lounge context:
{airport_context}

Question:
I have an Amex Platinum and I am flying from JFK.
What Centurion Lounge can I use and where is it?

Give a concise answer that includes:
- whether the card provides access
- lounge location
- hours
- any important entry requirements mentioned in the context
"""

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
)

response = model.invoke(prompt)

print("\n=== GENERATED ANSWER ===")
print(response.text)

print("\n=== CARD POLICY ===")

for document in policy_results:
    print(document.metadata["chunk_id"])
    print(document.page_content)
    print()


print("\n=== AIRPORT LOUNGE ===")

for document in airport_results:
    print(document.metadata["chunk_id"])
    print(document.page_content)
    print()