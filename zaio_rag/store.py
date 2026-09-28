import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict[str, Any]
    embedding: list[float]


@dataclass(frozen=True)
class SearchResult:
    text: str
    metadata: dict[str, Any]
    score: float


class SQLiteVectorStore:
    """Small persistent cosine-search store suitable for a single-process project."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )"""
            )

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def replace_all(self, documents: list[Document]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM documents")
            connection.executemany(
                "INSERT INTO documents (id, text, metadata, embedding) VALUES (?, ?, ?, ?)",
                [
                    (
                        document.id,
                        document.text,
                        json.dumps(document.metadata),
                        json.dumps(document.embedding),
                    )
                    for document in documents
                ],
            )

    def search(self, embedding: list[float], top_k: int = 4) -> list[SearchResult]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT text, metadata, embedding FROM documents"
            ).fetchall()

        results = []
        for text, metadata_json, vector_json in rows:
            vector = json.loads(vector_json)
            if len(vector) != len(embedding):
                continue
            denominator = math.sqrt(sum(value * value for value in embedding)) * math.sqrt(
                sum(value * value for value in vector)
            )
            score = (
                sum(left * right for left, right in zip(embedding, vector)) / denominator
                if denominator
                else 0.0
            )
            results.append(
                SearchResult(text, json.loads(metadata_json), float(score))
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def count(self) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]