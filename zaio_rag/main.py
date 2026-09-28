from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from fastapi.staticfiles import StaticFiles

from .service import RAGService, create_default_service


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, question: str) -> str:
        if not question.strip():
            raise ValueError("question must contain non-whitespace text")
        return question


def create_app(service: RAGService | None = None) -> FastAPI:
    application = FastAPI(title="ZAIO RAG Assistant", version="1.0.0")
    rag_service = service or create_default_service()
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    application.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    @application.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(frontend_dir / "index.html")

    @application.get("/health")
    def health():
        return {"status": "ok", "indexed_chunks": rag_service.store.count()}

    @application.post("/ask")
    def ask(request: AskRequest):
        return rag_service.ask(request.question.strip())

    return application


app = create_app()