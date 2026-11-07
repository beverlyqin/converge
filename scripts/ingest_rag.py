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

source_id = "jfk_centurion"

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
    string=lambda text: text and "Terminal 4" in text
)

if text_node is None:
    raise ValueError("JFK location section not found")

container = text_node.parent.parent

paragraphs = container.find_all(
    "p",
    recursive=False,
)

location_text = "\n".join(
    paragraph.get_text(" ", strip=True)
    for paragraph in paragraphs[:2]
)

cleaned_text = (
    "## JFK Centurion Lounge\n\n"
    f"{location_text}"
)

cleaned_dir = project_root / "data" / "rag" / "cleaned"
cleaned_dir.mkdir(parents=True, exist_ok=True)

cleaned_path = cleaned_dir / f'{source["id"]}.md'

cleaned_path.write_text(
    cleaned_text,
    encoding="utf-8",
)

print(f"Cleaned characters: {len(cleaned_text):,}")
print(f"Cleaned text saved to: {cleaned_path}")


print(f"Downloaded: {source['source_name']}")
print(f"Status: {response.status_code}")
print(f"Characters: {len(response.text):,}")

