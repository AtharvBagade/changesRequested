"""Chunk text and metadata in SQLite, vectors in a numpy file.

Row i of the vectors file is the embedding of the chunk with id i.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CHUNKS_FILE = "chunks.sqlite"
VECTORS_FILE = "vectors.npy"

SCHEMA = """
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    file TEXT NOT NULL,
    symbol TEXT,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    text TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class Chunk:
    file: str
    symbol: str | None
    start_line: int
    end_line: int
    text: str


def write_store(directory: Path, chunks: list[Chunk], vectors: np.ndarray) -> None:
    """Replace any store in directory with these chunks and vectors."""
    if vectors.ndim != 2 or len(vectors) != len(chunks):
        raise ValueError(
            f"need one vector row per chunk: {len(chunks)} chunks, "
            f"vectors of shape {vectors.shape}"
        )
    directory.mkdir(parents=True, exist_ok=True)
    db_path = directory / CHUNKS_FILE
    db_path.unlink(missing_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute(SCHEMA)
        db.executemany(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
            [
                (i, c.file, c.symbol, c.start_line, c.end_line, c.text)
                for i, c in enumerate(chunks)
            ],
        )
    db.close()
    np.save(directory / VECTORS_FILE, vectors.astype(np.float32))


def read_store(directory: Path) -> tuple[list[Chunk], np.ndarray]:
    """Load the chunks, in id order, and their vectors."""
    db = sqlite3.connect(directory / CHUNKS_FILE)
    try:
        rows = db.execute(
            "SELECT file, symbol, start_line, end_line, text FROM chunks ORDER BY id"
        ).fetchall()
    finally:
        db.close()
    vectors = np.load(directory / VECTORS_FILE)
    return [Chunk(*row) for row in rows], vectors
