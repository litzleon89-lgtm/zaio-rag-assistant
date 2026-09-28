import re


def split_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split normalized text into overlapping word-bounded chunks."""
    words = re.sub(r"\s+", " ", text).strip().split()
    if not words:
        return []
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap smaller than it")

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks