import sys
import types
from pathlib import Path

import numpy as np
import pytest

from changesrequested.config import ConfigError, Settings, read_config
from changesrequested.indexing.embed import embed
from changesrequested.indexing.store import Chunk, read_store, write_store

REPO_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"

CHUNKS = [
    Chunk("pkg/a.py", None, 1, 4, '"""Module a."""\nimport os\n'),
    Chunk("pkg/a.py", "foo", 6, 9, "def foo(x):\n    return x + 1\n"),
    Chunk("pkg/b.py", "Bar.baz", 10, 20, "    def baz(self):\n        ünïcode\n"),
]


def test_round_trip(tmp_path: Path) -> None:
    vectors = np.random.default_rng(0).random((3, 8), dtype=np.float32)

    write_store(tmp_path, CHUNKS, vectors)
    chunks, loaded = read_store(tmp_path)

    assert chunks == CHUNKS
    np.testing.assert_array_equal(loaded, vectors)
    assert loaded.dtype == np.float32


def test_rewrite_replaces_old_store(tmp_path: Path) -> None:
    write_store(tmp_path, CHUNKS, np.zeros((3, 8)))
    write_store(tmp_path, CHUNKS[:1], np.ones((1, 8)))

    chunks, vectors = read_store(tmp_path)

    assert chunks == CHUNKS[:1]
    assert vectors.shape == (1, 8)


def test_vector_count_must_match_chunks(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="3 chunks"):
        write_store(tmp_path, CHUNKS, np.zeros((2, 8)))


def test_committed_config_fixes_embedding_model() -> None:
    assert read_config(REPO_CONFIG).settings.embedding_model


def test_embed_uses_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: list[str] = []

    class FakeModel:
        def __init__(self, name: str) -> None:
            loaded.append(name)

        def encode(self, texts, normalize_embeddings, convert_to_numpy):
            assert normalize_embeddings and convert_to_numpy
            return np.ones((len(texts), 4), dtype=np.float64)

    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)

    vectors = embed(["a", "b"], Settings(embedding_model="some/model"))

    assert loaded == ["some/model"]
    assert vectors.shape == (2, 4)
    assert vectors.dtype == np.float32


def test_embed_without_model_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="embedding_model"):
        embed(["a"], Settings())
