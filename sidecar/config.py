import os
from pathlib import Path

SIDECAR_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RAG_DB_PATH", str(SIDECAR_DIR / "rag.db")))
CORPUS_DIR = SIDECAR_DIR / "sample_corpus"
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.environ.get("RAG_SIM_THRESHOLD", "0.08"))
