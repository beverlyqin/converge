import json
import nltk
import re
from pathlib import Path

from transformers import AutoTokenizer
from langchain_text_splitters import MarkdownHeaderTextSplitter
from nltk.tokenize import sent_tokenize
from langchain_core.documents import Document


nltk.download("punkt_tab", quiet=True)

project_root = Path(__file__).resolve().parents[1]

cleaned_dir = project_root / "data" / "rag" / "cleaned"
sources_path = project_root / "data" / "rag" / "sources.json"
chunks_path = project_root / "data" / "rag" / "chunks.json"


def chunk_by_sentence(text, tokenizer, max_tokens=200):
    sentences = sent_tokenize(text)

    chunks = []
    current_sentences = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = len(
            tokenizer.encode(
                sentence,
                add_special_tokens=False,
            )
        )

        if (
            current_sentences
            and current_tokens + sentence_tokens > max_tokens
        ):
            chunks.append(" ".join(current_sentences))

            # One full sentence of overlap
            current_sentences = [current_sentences[-1]]

            current_tokens = len(
                tokenizer.encode(
                    current_sentences[0],
                    add_special_tokens=False,
                )
            )

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


sources = json.loads(
    sources_path.read_text(encoding="utf-8")
)

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("##", "section"),
    ]
)

tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2"
)

chunks = []

def infer_lounge_network(section):
    mapping = {
        "The Centurion Lounge": "Centurion Lounge",
        "Delta Sky Club": "Delta Sky Club",
        "Escape Lounges": "Escape Lounge",
        "Plaza Premium Lounges": "Plaza Premium Lounge",
        "Priority Pass": "Priority Pass",
    }

    return mapping.get(section)

for source in sources:
    cleaned_path = cleaned_dir / f'{source["id"]}.md'

    if not cleaned_path.exists():
        continue

    markdown = cleaned_path.read_text(
        encoding="utf-8"
    )

    section_documents = header_splitter.split_text(
        markdown
    )

    for section_document in section_documents:
        section_chunks = chunk_by_sentence(
            section_document.page_content,
            tokenizer,
            max_tokens=200,
        )

        section = section_document.metadata["section"]

        section_slug = re.sub(
            r"[^a-z0-9]+",
            "_",
            section.lower(),
        ).strip("_")

        for chunk_number, text in enumerate(
            section_chunks,
            start=1,
        ):
            metadata = {
                **section_document.metadata,
                "chunk_id": (
                    f'{source["id"]}::'
                    f"{section_slug}::"
                    f"{chunk_number}"
                ),
                "source_id": source["id"],
                "source_name": source["source_name"],
                "url": source["url"],
                "provider": source["provider"],
                "document_type": source["document_type"],
                "card": source.get("card"),
                "airport": source.get("airport"),
                "lounge_network": (
                    source.get("lounge_network")
                    or infer_lounge_network(section)
                ),
                "retrieved_at": source.get("retrieved_at"),
            }
                
            chunks.append(
                Document(
                    page_content=text,
                    metadata=metadata,
                )
            )



chunk_data = [
    {
        "content": chunk.page_content,
        "metadata": chunk.metadata,
    }
    for chunk in chunks
]

chunks_path.write_text(
    json.dumps(chunk_data, indent=2),
    encoding="utf-8",
)


print(f"Saved {len(chunks)} chunks to: {chunks_path}")

for source in sources:
    count = sum(
        1
        for chunk in chunks
        if chunk.metadata["source_id"] == source["id"]
    )

    if count:
        print(f"{source['id']}: {count} chunks")

# temp
for chunk in chunks:
    if chunk.metadata["source_id"] == "delta_reserve_centurion_access":
        print("\n" + chunk.metadata["chunk_id"])
        print(chunk.page_content)