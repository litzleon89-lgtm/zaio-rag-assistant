import math
import re

from .answering import GroundedAnswerer
from .config import MIN_SIMILARITY, REFUSAL, TOP_K
from .store import SQLiteVectorStore


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "handbook", "have", "how", "i", "in", "is", "it", "me", "of", "on", "or", "our",
    "about", "available", "last", "name", "please", "say", "should", "tell", "that", "the", "their", "them", "there",
    "these", "they", "this", "to", "us", "was", "we", "were", "what",
    "when", "where", "which", "who", "whom", "why", "will", "with",
    "would", "you", "your", "zaio", "offer",
}
_CATALOG_NAMES = (
    "Fullstack AI Engineer",
    "Cloud & DevOps Engineering",
    "Fullstack Web Development",
    "Data Science",
    "Cybersecurity",
    "Digital Marketing",
)


def _content_terms(text: str) -> set[str]:
    terms = set()
    normalized_text = re.sub(r"\bboot[\s-]+camp\b", "bootcamp", text.lower())
    for term in re.findall(r"[a-z0-9]+", normalized_text):
        if len(term) > 2 and term not in _STOP_WORDS:
            if term in {"communicate", "communicates", "communicated", "communication", "communications"}:
                term = "communicat"
            elif term in {"course", "courses", "bootcamp", "bootcamps", "class", "classes"}:
                term = "course"
            elif term in {"need", "needs", "essential", "essentials", "require", "requires", "required", "requirement", "requirements"}:
                term = "need"
            elif term == "classes":
                term = "course"
            elif term.endswith("ies") and len(term) > 4:
                term = term[:-3] + "y"
            elif term.endswith("s") and not term.endswith("ss"):
                term = term[:-1]
            terms.add(term)
    return terms


def _is_course_catalog_question(question: str) -> bool:
    asks_for_list = re.search(
        r"\b(what|which|list|name|show|all|every)\b.{0,50}\b(courses|bootcamps)\b",
        question,
        re.IGNORECASE,
    )
    asks_what_zaio_offers = re.search(
        r"\b(courses?|bootcamps?)\b.{0,40}\b(offer|offers|provide|provides)\b",
        question,
        re.IGNORECASE,
    )
    return bool(asks_for_list or asks_what_zaio_offers)


class RAGService:
    def __init__(self, store, embedder, answerer=None):
        self.store = store
        self.embedder = embedder
        self.answerer = answerer or GroundedAnswerer()

    def ask(self, question: str) -> dict[str, str | None]:
        query_vector = self.embedder.embed([question])[0]
        query_terms = _content_terms(question)
        catalog_question = _is_course_catalog_question(question)
        communication_policy_question = bool(
            "communicat" in query_terms
            and query_terms & {"course", "orientation", "student"}
        )
        handbook_question = bool(
            re.search(r"\b(handbook|student handbook)\b", question, re.IGNORECASE)
            or communication_policy_question
        )
        candidate_count = (
            self.store.count()
            if catalog_question or handbook_question
            else max(TOP_K * 10, 40)
        )
        matches = self.store.search(query_vector, top_k=candidate_count)
        if handbook_question:
            matches = [
                match
                for match in matches
                if match.metadata.get("source") == "Student Handbook"
            ]
        elif catalog_question:
            matches = [
                match
                for match in matches
                if match.metadata.get("source") == "ZAIO Website"
                and re.search(
                    r"/(?:compare-courses|bootcamps|[^/]*-bootcamp)?/?$",
                    match.metadata.get("url", ""),
                    re.IGNORECASE,
                )
            ]
        minimum_similarity = 0.25 if communication_policy_question else MIN_SIMILARITY
        relevant = [match for match in matches if match.score >= minimum_similarity]
        if catalog_question:
            relevant.extend(
                match
                for match in matches
                if 0.28 <= match.score < MIN_SIMILARITY
                and match not in relevant
            )
        if query_terms:
            minimum_term_matches = max(1, math.ceil(len(query_terms) * 0.6))
            relevant = [
                match
                for match in relevant
                if len(query_terms & _content_terms(match.text)) >= minimum_term_matches
            ]
        if catalog_question:
            relevant.sort(
                key=lambda match: (
                    0
                    if "/compare-courses" in match.metadata.get("url", "")
                    else 1,
                    -_catalog_coverage(match.text),
                    -match.score,
                )
            )
        elif communication_policy_question:
            relevant.sort(
                key=lambda match: (
                    -len(query_terms & _content_terms(match.text)),
                    -match.score,
                )
            )
        relevant = relevant[:TOP_K]
        if not relevant:
            return {"answer": REFUSAL, "source": None}

        primary_source = relevant[0].metadata
        citation_key = "page" if primary_source.get("source") == "Student Handbook" else "url"
        citation_value = primary_source.get(citation_key)
        cited_results = [
            match
            for match in relevant
            if match.metadata.get("source") == primary_source.get("source")
            and match.metadata.get(citation_key) == citation_value
        ]
        if catalog_question:
            answer = _catalog_answer(cited_results)
        else:
            answer = self.answerer.answer(question, cited_results)
        if not answer or answer.strip() == REFUSAL:
            return {"answer": REFUSAL, "source": None}
        if primary_source.get("source") == "Student Handbook":
            source_label = f"Student Handbook - Page {primary_source['page']}"
        else:
            source_label = primary_source.get("url", "ZAIO Website")
        return {"answer": answer, "source": source_label}


def _catalog_coverage(text: str) -> int:
    normalized = text.lower()
    return sum(name.lower() in normalized for name in _CATALOG_NAMES)


def _catalog_answer(results) -> str:
    context = " ".join(result.text for result in results).lower()
    names = [name for name in _CATALOG_NAMES if name.lower() in context]
    if names:
        return "ZAIO lists these bootcamps: " + ", ".join(names) + "."
    return GroundedAnswerer().answer("What bootcamps does ZAIO offer?", results)


def create_default_service():
    from .config import DATABASE_PATH, EMBEDDING_MODEL
    from .embeddings import SentenceTransformerEmbedder

    return RAGService(
        store=SQLiteVectorStore(DATABASE_PATH),
        embedder=SentenceTransformerEmbedder(EMBEDDING_MODEL),
    )