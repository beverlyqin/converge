import json
from pathlib import Path
from bs4 import BeautifulSoup

import httpx


project_root = Path(__file__).resolve().parents[1]

sources_path = project_root / "data" / "rag" / "sources.json"
raw_dir = project_root / "data" / "rag" / "raw"

raw_dir.mkdir(parents=True, exist_ok=True)

with sources_path.open() as file:
    sources = json.load(file)

source_id = "delta_reserve_centurion_access"

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

soup = BeautifulSoup(response.text, "html.parser")

text_node = soup.find(
    string=lambda text: (
        text
        and "Delta SkyMiles" in text
        and "Reserve Card Members" in text
    )
)

heading = soup.find(
    string=lambda text: (
        text
        and "Delta SkyMiles" in text
        and "Reserve Card Members" in text
    )
)

if heading is None:
    raise ValueError("Delta Reserve section not found")

heading_element = heading.parent.parent

section_parts = [
    "## Delta SkyMiles Reserve Card Members"
]

for sibling in heading_element.find_next_siblings():
    text = sibling.get_text(
        " ",
        strip=True,
    )

    if text.startswith("Sidecar by The Centurion"):
        break

    section_parts.append(text)

cleaned_text = "\n\n".join(section_parts)

cleaned_dir = project_root / "data" / "rag" / "cleaned"
cleaned_dir.mkdir(parents=True, exist_ok=True)

cleaned_path = (
    cleaned_dir
    / f'{source["id"]}.md'
)

cleaned_path.write_text(
    cleaned_text,
    encoding="utf-8",
)

print(f"Cleaned characters: {len(cleaned_text):,}")
print(f"Cleaned text saved to: {cleaned_path}")

output_path = raw_dir / f'{source["id"]}.html'

output_path.write_text(
    response.text,
    encoding="utf-8",
)

print(f"Downloaded: {source['source_name']}")
print(f"Status: {response.status_code}")
print(f"Saved to: {output_path}")
print(f"Characters: {len(response.text):,}")

