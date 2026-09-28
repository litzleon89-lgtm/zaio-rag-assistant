# ZAIO RAG Assistant

FastAPI assistant that retrieves from the Student Handbook PDF and public pages on [zaio.io](https://www.zaio.io/), then answers only from retrieved passages. Website chunks retain their URL; handbook chunks retain their PDF page number. If retrieval is below the configured relevance threshold, the API returns exactly: `I could not find that information in the available knowledge base.`

## Setup

Use Python 3.11-3.13. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The complete 26-page handbook PDF is at `data/student_handbook.pdf`; ingestion automatically prefers it over the secondary Canva HTML export. PDF text is normalized before chunking, and page metadata is retained for citations. The HTML export remains as a fallback only.

## Index the Knowledge Base

```powershell
python -m zaio_rag.ingest
```

The crawler starts at `https://www.zaio.io/`, follows same-domain HTML links up to 30 pages, strips navigation and other page chrome, and stores all chunk text, metadata, and local sentence-transformer embeddings in `.data/knowledge.sqlite3`. Adjust the crawl depth or PDF path with:

```powershell
python -m zaio_rag.ingest --handbook .\data\student_handbook.pdf --max-pages 50
```

The first indexing run downloads the configured embedding model (`all-MiniLM-L6-v2`). Re-run ingestion when either source changes; the database is rebuilt from both sources.

## Run the API

```powershell
uvicorn zaio_rag.main:app --reload --port 8001
```

`POST http://127.0.0.1:8001/ask` accepts `{"question":"What courses does ZAIO offer?"}` and returns an answer with the retrieved source URL, such as `https://www.zaio.io/compare-courses`, or a handbook citation such as `Student Handbook - Page 18`. Explicit handbook questions search handbook chunks only; unsupported questions return the required refusal and a `null` source. `GET /health` reports the indexed chunk count; `/docs` provides Swagger UI.

By default, answer synthesis is extractive and does not need an API key. To enable concise model-written synthesis over retrieved text only, set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`). `MIN_SIMILARITY` (default `0.35`) and `TOP_K` (default `4`) tune retrieval conservatism and context size.

## Tests and Test Cases

```powershell
pytest -q
```

See [test_cases.md](test_cases.md) for handbook, website, and out-of-scope cases. The full 26-page PDF is indexed and handbook answers include PDF page citations.

## n8n

The workflow in [n8n/zaio-rag-workflow.json](n8n/zaio-rag-workflow.json) was imported into n8n 2.40.7 and its production webhook was tested successfully. It targets `http://127.0.0.1:8001/ask` for native n8n on the same host as the API. For Docker Desktop n8n, change the HTTP Request node URL to `http://host.docker.internal:8001/ask`. Activate the webhook and send a POST request containing `{"question":"..."}` to `/webhook/zaio-rag-ask`; the workflow forwards it to `/ask` and returns the answer and source.

## Submission / Demo Checklist

- Include `data/student_handbook.pdf` in the repository or deliver it separately if file-size rules require it.
- Re-run `pytest -q` after changes and record the real results in [test_cases.md](test_cases.md).
- Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md) to record indexing, handbook citations, a ZAIO website answer, a refused question, and the n8n webhook in a 5-10 minute Loom video.