import json
import nltk
from pathlib import Path
from collections import Counter

from transformers import AutoTokenizer
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter
)
from nltk.tokenize import sent_tokenize
from langchain_core.documents import Document


nltk.download("punkt_tab")

project_root = Path(__file__).resolve().parents[1]

cleaned_path=(
    project_root
    / "data"
    / "rag"
    / "cleaned"
    / "amex_platinum_lounge_terms.md"
)

srouces_path = project_root / "data" / "rag" / "sources.json"

markdown = cleaned_path.read_text(encoding="utf-8")

with srouces_path.open() as file:
    sources = json.load(file)

source = next(
    source
    for source in sources
    if source["id"] == "amex_platinum_lounge_terms"
)

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("##", "section"),
    ]
)

section_documents = header_splitter.split_text(markdown)

tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2"
)

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

chunks = []

for section_document in section_documents:
    section_chunks = chunk_by_sentence(
        section_document.page_content,
        tokenizer,
        max_tokens=200,
    )

    for text in section_chunks:
        chunks.append(
            Document(
                page_content=text,
                metadata=section_document.metadata.copy(),
            )
        )

for i, chunk in enumerate(chunks):
    chunk.metadata.update(
        {
            "source_id": source["id"],
            "source_name": source["source_name"],
            "url": source["url"],
            "provider": source["provider"],
            "document_type": source["document_type"],
            "card": source["card"],
        }
    )
    section = chunk.metadata.get("section")

    if section:
        chunk.page_content = (
            f"{section}\n\n{chunk.page_content}"
        )

    print(f"\n--- Chunk {i} ---")
    print(chunk.metadata)
    print(chunk.page_content)

# inspect chunks
section_counts = Counter(
    chunk.metadata.get("section")
    for chunk in chunks
)

print(f"Total chunks: {len(chunks)}")

for section, count in section_counts.items():
    print(f"{section}: {count} chunks")


seen_sections = set()

for chunk in chunks:

        print(f"\n--- {section} ---")
        print(chunk.page_content)

for i, chunk in enumerate(chunks):
    token_count = len(
        tokenizer.encode(
            chunk.page_content,
            add_special_tokens=False,
        )
    )

    print(f"\n--- Chunk {i} ({token_count} tokens) ---")
    print(chunk.metadata)
    print(chunk.page_content)

chunks_path = project_root / "data" / "rag" / "chunks.json"

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