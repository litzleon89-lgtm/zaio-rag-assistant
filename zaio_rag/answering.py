import os
import re

from .config import OPENAI_MODEL
from .store import SearchResult


class GroundedAnswerer:
    def __init__(self):
        self._client = None

    def _openai_client(self):
        if not os.getenv("OPENAI_API_KEY"):
            return None
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def answer(self, question: str, results: list[SearchResult]) -> str:
        context = "\n\n".join(result.text for result in results)
        client = self._openai_client()
        if client is not None:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Answer the question using only the supplied knowledge-base "
                            "context. Do not add outside facts. If the context does not "
                            "contain the answer, reply exactly: I could not find that "
                            "information in the available knowledge base."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nContext:\n{context}",
                    },
                ],
            )
            return (response.choices[0].message.content or "").strip()

        return self._extractive_answer(question, context)

    @staticmethod
    def _extractive_answer(question: str, context: str) -> str:
        terms = {
            term.lower()
            for term in re.findall(r"[A-Za-z0-9]+", question)
            if len(term) > 2
        }
        sentences = re.split(r"(?<=[.!?])\s+", context)
        ranked = sorted(
            enumerate(sentences),
            key=lambda item: (
                sum(term in item[1].lower() for term in terms),
                -item[0],
            ),
            reverse=True,
        )
        selected = [sentence.strip() for _index, sentence in ranked[:3] if sentence.strip()]
        return " ".join(selected) or context[:700]