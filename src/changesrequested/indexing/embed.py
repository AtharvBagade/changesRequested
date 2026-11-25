"""Embed text with the one sentence-transformers model fixed in config.yaml."""

import numpy as np

from changesrequested.config import ConfigError, Settings


def embedding_model_id(settings: Settings) -> str:
    if not settings.embedding_model:
        raise ConfigError("settings.embedding_model is not set in config.yaml")
    return settings.embedding_model


def embed(texts: list[str], settings: Settings) -> np.ndarray:
    """Unit-length float32 vectors, one row per text, for cosine search."""
    # Imported here so commands that never embed do not load torch.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(embedding_model_id(settings))
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype(np.float32)
