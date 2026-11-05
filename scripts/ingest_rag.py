import json
from pathlib import Path
from bs4 import BeautifulSoup

import httpx

project_root = Path(__file__).resolve().parents[1]

sources_path = Path("data/rag/sources.json")
raw_dir = Path("data/rag/raw")
cleaned_dir = project_root / "data" / "rag" / "cleaned"

raw_dir.mkdir(parents=True, exist_ok=True)

with sources_path.open() as file:
    sources = json.load(file)

source = sources[0]

response = httpx.get(
    source["url"],
    headers={
        "User-Agent": (
            "Mozilla/5.0 FlightMeetupRAG/1.0"
        )
    },
    follow_redirects=True,
    timeout=30.0,
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
for element in soup.find_all(
    id=lambda value: value and value.startswith("terms-")
):
    print(element["id"])

for element in soup(["script", "style", "noscript", "svg"]):
    element.decompose()

phrase = "U.S. Platinum Card Members have unlimited complimentary access"

text_node = soup.find(
    string=lambda text: text and phrase in text
)

if text_node:
    element = text_node.parent

    for level in range(6):
        print(
            f"Level {level}:",
            f"tag={element.name}",
            f"id={element.get('id')}",
            f"class={element.get('class')}",
        )

        element = element.parent

term_sections = [
    "terms-the-american-express-global-lounge-collection",
    "terms-the-centurion-lounge",
    "terms-escape-lounges",
    "terms-delta-sky-club",
    "terms-plaza-premium-lounges",
    "terms-priority-pass",
    "terms-additional-global-lounge-collection-partner-lounges",
]

cleaned_sections = []

for section_id in term_sections:
    section = soup.find(id=section_id)

    if section is None:
        continue

    title = section_id.removeprefix("terms-").replace("-", " ").title()

    text = section.get_text(
        separator="\n",
        strip=True,
    )

    cleaned_sections.append(
        f"## {title}\n\n{text}"
    )

cleaned_text = "\n\n".join(cleaned_sections)

cleaned_path = (
    project_root
    / "data"
    / "rag"
    / "cleaned"
    / f'{source["id"]}.md'
)

cleaned_path.parent.mkdir(parents=True, exist_ok=True)
cleaned_path.write_text(
    cleaned_text,
    encoding="utf-8",
)

for section in cleaned_sections:
    lines = section.splitlines()
    title = lines[0]
    print(f"{title}: {len(section):,} characters")
    
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