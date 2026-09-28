import argparse
import hashlib
import re
from pathlib import Path

from pypdf import PdfReader
from bs4 import BeautifulSoup

from .chunking import split_text
from .config import DATABASE_PATH, DEFAULT_HANDBOOK_PATH, EMBEDDING_MODEL
from .crawler import crawl_zaio
from .embeddings import SentenceTransformerEmbedder
from .store import Document, SQLiteVectorStore


def normalize_pdf_text(text: str) -> str:
    """Repair PDF text layers that insert spaces between every character."""
    spaced_word = re.compile(r"(?<!\S)(?:[A-Za-z0-9-] ){1,}[A-Za-z0-9-](?!\S)")
    normalized = spaced_word.sub(lambda match: match.group(0).replace(" ", ""), text)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return re.sub(r" *\n *", "\n", normalized).strip()


def load_handbook(path: str | Path) -> list[tuple[str, dict]]:
    handbook_path = Path(path)
    if not handbook_path.is_file():
        return []

    if handbook_path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(
            handbook_path.read_text(encoding="utf-8", errors="replace"), "html.parser"
        )
        for element in soup.select(
            "script, style, noscript, svg, nav, header, footer, aside, form, iframe, "
            "button, [role='toolbar'], div[aria-hidden='true'][id^='_r_']"
        ):
            element.decompose()
        for text_node in soup.find_all(string=lambda value: value and value.strip() in {
            "A", "White", "Dark blue background"
        }):
            text_node.replace_with(" ")
        content = soup.body or soup
        text = " ".join(content.stripped_strings)
        page_match = re.search(r"\bPage\s+(\d+)\s+of\s+\d+\b", text, re.IGNORECASE)
        page_number = int(page_match.group(1)) if page_match else None
        return [
            (chunk, {"source": "Student Handbook", **({"page": page_number} if page_number else {})})
            for chunk in split_text(text)
        ]

    pages = []
    for page_number, page in enumerate(PdfReader(str(handbook_path)).pages, start=1):
        text = normalize_pdf_text(page.extract_text() or "")
        pages.extend(
            (chunk, {"source": "Student Handbook", "page": page_number})
            for chunk in split_text(text)
        )
    return pages


def build_documents(handbook_path: str | Path, max_pages: int = 30):
    entries = load_handbook(handbook_path)
    for page in crawl_zaio(max_pages=max_pages):
        entries.extend(
            (chunk, {"source": "ZAIO Website", "url": page.url})
            for chunk in split_text(page.text)
        )
    return entries


def ingest(handbook_path: str | Path, max_pages: int = 30) -> int:
    entries = build_documents(handbook_path, max_pages=max_pages)
    if not entries:
        raise RuntimeError("No content was extracted from the PDF or ZAIO website.")

    embedder = SentenceTransformerEmbedder(EMBEDDING_MODEL)
    vectors = embedder.embed([text for text, _metadata in entries])
    documents = []
    for index, ((text, metadata), vector) in enumerate(zip(entries, vectors)):
        identity = f"{metadata}|{index}|{text}"
        document_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        documents.append(Document(document_id, text, metadata, vector))

    store = SQLiteVectorStore(DATABASE_PATH)
    store.replace_all(documents)
    return len(documents)


def main():
    parser = argparse.ArgumentParser(description="Index the ZAIO site and handbook PDF")
    parser.add_argument("--handbook", type=Path, default=DEFAULT_HANDBOOK_PATH)
    parser.add_argument("--max-pages", type=int, default=30)
    args = parser.parse_args()

    if not args.handbook.is_file():
        print(f"Handbook not found at {args.handbook}; indexing the website only.")
    count = ingest(args.handbook, args.max_pages)
    print(f"Indexed {count} chunks in {DATABASE_PATH}")


if __name__ == "__main__":
    main()