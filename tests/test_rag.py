from fastapi.testclient import TestClient

from zaio_rag.chunking import split_text
from zaio_rag.crawler import clean_page, crawl_zaio
from zaio_rag.ingest import load_handbook, normalize_pdf_text
from zaio_rag.main import create_app
from zaio_rag.service import RAGService
from zaio_rag.store import Document, SQLiteVectorStore


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, 0.0] for _text in texts]


class FakeAnswerer:
    def answer(self, question, results):
        return "ZAIO offers a Fullstack Web Development bootcamp."


def test_split_text_overlaps_and_covers_all_words():
    chunks = split_text("one two three four five six seven", chunk_size=4, overlap=1)
    assert chunks == ["one two three four", "four five six seven"]


def test_load_handbook_html_removes_viewer_controls_and_keeps_page(tmp_path):
    handbook = tmp_path / "handbook.html"
    handbook.write_text(
        "<html><body><nav>Canva controls</nav>"
        "<main><p>Handbook title.</p></main>"
        "<div aria-hidden='true'><p>Page 3 of 24.</p>"
        "<p>Attendance policy details.</p></div>"
        "<div id='_r_4_' aria-hidden='true'>Toolbar</div>"
        "<button>Next page</button></body></html>",
        encoding="utf-8",
    )

    chunks = load_handbook(handbook)
    assert chunks == [
        (
            "Handbook title. Page 3 of 24. Attendance policy details.",
            {"source": "Student Handbook", "page": 3},
        )
    ]


def test_normalize_letter_spaced_pdf_text():
    raw = "W e l c o m e\nF u l l - S t a c k  A I  B o o t c a m p"
    assert normalize_pdf_text(raw) == "Welcome\nFull-Stack AI Bootcamp"


def test_clean_page_removes_navigation_and_footer():
    cleaned = clean_page(
        "<html><body><nav>Menu links</nav><main><p>Course details</p></main>"
        "<footer>Copyright</footer></body></html>"
    )
    assert cleaned == "Course details"


def test_crawler_follows_only_zaio_html_pages(monkeypatch):
    pages = {
        "https://www.zaio.io/": (
            '<html><body><main>Home content</main><a href="/courses">Courses</a>'
            '<a href="https://example.org/">External</a></body></html>'
        ),
        "https://www.zaio.io/courses": (
            "<html><body><main>Course content</main></body></html>"
        ),
    }

    class Response:
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class Session:
        headers = {}

        def get(self, url, timeout):
            return Response(pages[url])

    monkeypatch.setattr("zaio_rag.crawler.requests.Session", Session)
    crawled = crawl_zaio(max_pages=5)
    assert [(page.url, page.text) for page in crawled] == [
        ("https://www.zaio.io/", "Home content"),
        ("https://www.zaio.io/courses", "Course content"),
    ]


def test_sqlite_vector_store_orders_by_cosine_similarity(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "best match", {"source": "ZAIO Website", "url": "https://www.zaio.io/"}, [1, 0]),
            Document("b", "weaker match", {"source": "Student Handbook", "page": 1}, [0, 1]),
        ]
    )
    results = store.search([1, 0], top_k=2)
    assert [result.text for result in results] == ["best match", "weaker match"]
    assert results[0].score == 1.0


def test_ask_returns_retrieved_source(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [Document("a", "Courses include Fullstack Web Development.", {"source": "ZAIO Website", "url": "https://www.zaio.io/"}, [1, 0])]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    response = TestClient(create_app(service)).post(
        "/ask", json={"question": "What courses does ZAIO offer?"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "ZAIO lists these bootcamps: Fullstack Web Development.",
        "source": "https://www.zaio.io/",
    }


def test_ask_refuses_low_relevance_match(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [Document("a", "Bootcamp details.", {"source": "ZAIO Website", "url": "https://www.zaio.io/"}, [0, 1])]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    response = TestClient(create_app(service)).post(
        "/ask", json={"question": "Who won an unrelated sports event?"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "I could not find that information in the available knowledge base.",
        "source": None,
    }


def test_ask_ignores_semantically_similar_handbook_cover(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Zaio Fullstack AI bootcamp handbook cover.", {"source": "Student Handbook", "page": 1}, [1, 0]),
            Document("b", "Courses include Fullstack Web Development and Data Science.", {"source": "ZAIO Website", "url": "https://www.zaio.io/compare-courses"}, [0.9, 0.1]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    result = service.ask("What courses does ZAIO offer?")
    assert result["source"] == "https://www.zaio.io/compare-courses"


def test_course_catalog_question_prefers_course_comparison_page(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Fullstack AI Engineer bootcamp details.", {"source": "ZAIO Website", "url": "https://www.zaio.io/fullstack-ai-engineer-bootcamp"}, [1, 0]),
            Document("b", "Compare bootcamps: Fullstack AI Engineer, Cloud and DevOps, Fullstack Web Development, Data Science, Cybersecurity, Digital Marketing.", {"source": "ZAIO Website", "url": "https://www.zaio.io/compare-courses"}, [0.3, 0.9539392014]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    result = service.ask("What courses does ZAIO offer?")
    assert result["source"] == "https://www.zaio.io/compare-courses"


def test_handbook_question_does_not_answer_from_website(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Student Handbook grading and assessment policy.", {"source": "Student Handbook", "page": 4}, [0.9, 0.1]),
            Document("b", "ZAIO bootcamp courses and grading options.", {"source": "ZAIO Website", "url": "https://www.zaio.io/bootcamps"}, [1, 0]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    result = service.ask("What does the handbook say about grading?")
    assert result["source"] == "Student Handbook - Page 4"


def test_ask_refuses_when_no_chunk_supports_question_terms(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "The bootcamp handbook welcomes students.", {"source": "Student Handbook", "page": 1}, [1, 0]),
            Document("b", "Zaio offers several bootcamps.", {"source": "ZAIO Website", "url": "https://www.zaio.io/bootcamps"}, [0.95, 0.05]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    assert service.ask("What is the grading breakdown?") == {
        "answer": "I could not find that information in the available knowledge base.",
        "source": None,
    }


def test_ask_refuses_when_only_one_query_term_matches(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Salary growth is anticipated from the second year onwards.", {"source": "Student Handbook", "page": 24}, [1, 0]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    assert service.ask("What was ZAIO revenue last year?") == {
        "answer": "I could not find that information in the available knowledge base.",
        "source": None,
    }


def test_ask_finds_handbook_communication_channels(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Before Orientation Day all communication will take place via email. After Orientation Day ongoing communication will transition to our Discord channel.", {"source": "Student Handbook", "page": 18}, [1, 0]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    result = service.ask("What does the handbook say about communication channels?")
    assert result["source"] == "Student Handbook - Page 18"


def test_ask_routes_communication_before_classes_to_handbook(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Before Orientation Day all payment fees must be paid before orientation day.", {"source": "Student Handbook", "page": 16}, [1, 0]),
            Document("b", "Before Orientation Day all communication will take place via email. After Orientation Day the boot camp officially begins and communication will transition to Discord.", {"source": "Student Handbook", "page": 18}, [0.9, 0.1]),
        ]
    )
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    result = service.ask("How does ZAIO communicate before classes start?")
    assert result["source"] == "Student Handbook - Page 18"


def test_ask_limits_answer_context_to_the_cited_page(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    store.replace_all(
        [
            Document("a", "Best match", {"source": "ZAIO Website", "url": "https://www.zaio.io/"}, [1, 0]),
            Document("b", "Another page", {"source": "ZAIO Website", "url": "https://www.zaio.io/courses"}, [0.9, 0.1]),
        ]
    )

    class RecordingAnswerer:
        def answer(self, question, results):
            assert [result.text for result in results] == ["Best match"]
            return "Grounded response."

    service = RAGService(store, FakeEmbedder(), RecordingAnswerer())
    response = TestClient(create_app(service)).post(
        "/ask", json={"question": "What does ZAIO offer?"}
    )
    assert response.status_code == 200
    assert response.json()["source"] == "https://www.zaio.io/"


def test_ask_rejects_whitespace_question(tmp_path):
    store = SQLiteVectorStore(tmp_path / "vectors.sqlite3")
    service = RAGService(store, FakeEmbedder(), FakeAnswerer())
    response = TestClient(create_app(service)).post("/ask", json={"question": "   "})
    assert response.status_code == 422