import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", PROJECT_ROOT / ".data"))
DATABASE_PATH = Path(os.getenv("RAG_DATABASE_PATH", DATA_DIR / "knowledge.sqlite3"))
DEFAULT_HANDBOOK_PATH = Path(
    os.getenv(
        "HANDBOOK_PATH",
        PROJECT_ROOT
        / "data"
        / (
            "student_handbook.pdf"
            if (PROJECT_ROOT / "data" / "student_handbook.pdf").is_file()
            else "student_handbook.html"
        ),
    )
)
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.35"))
TOP_K = int(os.getenv("TOP_K", "4"))
REFUSAL = "I could not find that information in the available knowledge base."