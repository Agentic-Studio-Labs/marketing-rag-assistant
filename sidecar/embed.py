from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import numpy as np

from config import EMBED_MODEL

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_lock = threading.Lock()
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer as ST

            _model = ST(EMBED_MODEL)
        return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    model = get_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)
