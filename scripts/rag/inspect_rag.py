from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

documents = [
    Document(
        page_content=(
            "The Centurion Lounge at JFK is in Terminal 4 on Level 4, "
            "just after security. It is open from 5 AM to 10 PM. "
            "Access is subject to eligibility and space availability."
        ),
        metadata={
            "type": "lounge",
            "airport": "JFK",
            "lounge": "Centurion Lounge",
            "source": "American Express",
        },
    ),
    Document(
        page_content=(
            "The Centurion Lounge at Miami International Airport is in "
            "North Terminal, Concourse D, near Gate D12 on the 4th floor. "
            "It is open from 5 AM to 10 PM."
        ),
        metadata={
            "type": "lounge",
            "airport": "MIA",
            "lounge": "Centurion Lounge",
            "source": "American Express",
        },
    ),
    Document(
        page_content=(
            "U.S. American Express Platinum Card members receive access "
            "to the Centurion Lounge network. Centurion Lounge entry "
            "requires an eligible card, government-issued ID, and a "
            "confirmed same-day boarding pass with a seat or boarding-zone "
            "assignment. Platinum Card members also receive 10 Delta Sky "
            "Club visits per year when traveling on an eligible Delta flight."
        ),
        metadata={
            "type": "credit_card",
            "card": "Amex Platinum",
            "source": "American Express",
        },
    ),
    Document(
        page_content=(
            "Delta SkyMiles Reserve American Express Card members receive "
            "15 Delta Sky Club visits each year when flying Delta. Unlimited "
            "Sky Club access can be unlocked after $75,000 in eligible card "
            "spend during a calendar year. The Reserve Card also provides "
            "Centurion Lounge access when the Delta flight is booked with "
            "the Reserve Card, subject to the lounge access terms."
        ),
        metadata={
            "type": "credit_card",
            "card": "Delta Reserve",
            "source": "American Express and Delta",
        },
    ),
]

vector_store = InMemoryVectorStore(
    HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
)

vector_store.add_documents(documents)
question = (
    "I have an Amex Platinum and I am flying from JFK. "
    "What lounge access might I have?"
)

results = vector_store.similarity_search(
    question,
    k=2,
)

for document in results:
    print(document.metadata)
    print(document.page_content)
    print()
context = "\n\n".join(
    document.page_content
    for document in results
)

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
)

response = llm.invoke(
    f"""
Answer the question using only the context below.

Question:
{question}

Context:
{context}

If the context does not contain enough information,
say that you do not know.
"""
)

print(response.text)