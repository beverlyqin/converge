import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


project_root = Path(__file__).resolve().parents[1]

sources_path = project_root / "data" / "rag" / "sources.json"
raw_dir = project_root / "data" / "rag" / "raw"

raw_dir.mkdir(parents=True, exist_ok=True)


sources = json.loads(
    sources_path.read_text(encoding="utf-8")
)


source_id = "jfk_delta_sky_club_b"

source = next(
    source
    for source in sources
    if source["id"] == source_id
)


response = httpx.get(
    source["url"],
    headers={
        "User-Agent": "Mozilla/5.0 FlightMeetupRAG/1.0"
    },
    follow_redirects=True,
    timeout=30.0,
)

response.raise_for_status()


# Save raw HTML
output_path = raw_dir / f'{source["id"]}.html'

output_path.write_text(
    response.text,
    encoding="utf-8",
)


# Inspect page structure around Gate 31
soup = BeautifulSoup(
    response.text,
    "html.parser",
)
text_node = soup.find(
    string=lambda text: (
        text
        and "Gate 31" in text
    )
)

if text_node is None:
    raise ValueError(
        "Gate 31 location text not found"
    )

container = text_node.parent.parent

location_parts = []

for child in container.find_all(
    recursive=False
):
    text = child.get_text(
        " ",
        strip=True,
    )

    if text and text != "Location":
        location_parts.append(text)

location_text = "\n".join(
    location_parts
)

cleaned_text = (
    f"## {source['source_name']}\n\n"
    f"{location_text}"
)

cleaned_dir = (
    project_root
    / "data"
    / "rag"
    / "cleaned"
)

cleaned_dir.mkdir(
    parents=True,
    exist_ok=True,
)

cleaned_path = (
    cleaned_dir
    / f'{source["id"]}.md'
)

cleaned_path.write_text(
    cleaned_text,
    encoding="utf-8",
)

print(
    f"Cleaned characters: "
    f"{len(cleaned_text):,}"
)

print(
    f"Cleaned text saved to: "
    f"{cleaned_path}"
)
# Location
text_node = soup.find(
    string=lambda text: (
        text
        and "Gate A8" in text
    )
)

if text_node is None:
    raise ValueError(
        "Gate A8 location text not found"
    )

container = text_node.parent.parent

print("\n--- Delta Sky Club A content ---")

for i, child in enumerate(
    container.find_all(recursive=False)
):
    text = child.get_text(
        " ",
        strip=True,
    )

    print(
        f"{i}: <{child.name}> "
        f"{text[:500]}"
    )


# Hours
print("\n--- Possible visible hours text ---")

for text_node in soup.find_all(
    string=lambda text: (
        text
        and (
            "5:00" in text
            or "10:30" in text
        )
    )
):
    parent = text_node.parent

    if parent.name in {
        "script",
        "style",
        "template",
    }:
        continue

    print(
        "tag:",
        parent.name,
        "class:",
        parent.get("class"),
        "text:",
        parent.get_text(
            " ",
            strip=True,
        )[:500],
    )

print(f"\nDownloaded: {source['source_name']}")
print(f"Status: {response.status_code}")
print(f"Saved to: {output_path}")
print(f"Characters: {len(response.text):,}")