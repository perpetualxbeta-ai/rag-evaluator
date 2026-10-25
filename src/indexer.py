"""Load, chunk and upsert documents into Postgres + pgvector.

Usage:
    python -m src.indexer --data-dir data/corpus --chunk-size 1000 --chunk-overlap 150
"""
from __future__ import annotations

import argparse
import logging
import os
import uuid
from pathlib import Path
from typing import Iterable, Sequence

import psycopg2
import psycopg2.errors
import psycopg2.extensions
import psycopg2.sql
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag"
)
COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION", "rag_eval")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_GLOBS: tuple[str, ...] = ("**/*.md", "**/*.txt")

# Stable namespace so the same chunk always gets the same ID (idempotent re-indexing).
_CHUNK_NAMESPACE = uuid.UUID("6f1c2a9e-3b7d-4e2a-9c51-8a0d4f7e2b13")


# --------------------------------------------------------------------------- #
# Shared helpers (also imported by eval/ scripts)
# --------------------------------------------------------------------------- #
def get_embeddings() -> Embeddings:
    """Single source of truth for the embedding model used at index *and* query time."""
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def get_vector_store(
    collection_name: str = COLLECTION_NAME,
    url: str = DATABASE_URL,
    embeddings: Embeddings | None = None,
    reset: bool = False,
) -> PGVector:
    return PGVector(
        embeddings=embeddings or get_embeddings(),
        collection_name=collection_name,
        connection=url,
        use_jsonb=True,
        pre_delete_collection=reset,
    )


def _libpq_dsn(url: str) -> str:
    """Strip the SQLAlchemy driver suffix so psycopg2 can consume the URL."""
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def require_openai_key() -> None:
    """Fail fast with a readable message instead of a deep OpenAI client traceback."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key == "sk-...":
        raise SystemExit(
            "OPENAI_API_KEY is not set. Copy .env.example to .env in the repo root "
            "and put your key on the OPENAI_API_KEY line (or export it in your shell)."
        )


def ensure_database(url: str = DATABASE_URL) -> None:
    """Create the target database if the server is reachable but the database is missing."""
    dsn = _libpq_dsn(url)
    try:
        psycopg2.connect(dsn).close()
        return
    except psycopg2.OperationalError as exc:
        if "does not exist" not in str(exc):
            raise SystemExit(
                f"Could not connect to Postgres using DATABASE_URL ({exc}). "
                "Is the pgvector container running? Check with `docker ps`."
            ) from exc

    params = psycopg2.extensions.parse_dsn(dsn)
    db_name = params.pop("dbname")
    admin = psycopg2.connect(**params, dbname="postgres")
    try:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(
                psycopg2.sql.SQL("CREATE DATABASE {}").format(psycopg2.sql.Identifier(db_name))
            )
        logger.info("Created database '%s'.", db_name)
    finally:
        admin.close()


def ensure_pgvector_extension(url: str = DATABASE_URL) -> None:
    """Create the database and the `vector` extension if they do not exist yet."""
    ensure_database(url)
    conn = psycopg2.connect(_libpq_dsn(url))
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            except psycopg2.errors.FeatureNotSupported as exc:
                raise SystemExit(
                    "The Postgres server at DATABASE_URL does not have pgvector installed. "
                    "Point DATABASE_URL at the pgvector/pgvector container instead."
                ) from exc
        logger.info("pgvector extension is available.")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Loading & chunking
# --------------------------------------------------------------------------- #
def load_documents(
    data_dir: str | Path, globs: Iterable[str] = DEFAULT_GLOBS
) -> list[Document]:
    root = Path(data_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Data directory not found: {root}")

    docs: list[Document] = []
    for pattern in globs:
        loader = DirectoryLoader(
            str(root),
            glob=pattern,
            loader_cls=TextLoader,
            loader_kwargs={"autodetect_encoding": True},
            use_multithreading=True,
            silent_errors=True,
        )
        docs.extend(loader.load())

    for doc in docs:
        # Store paths relative to the corpus root so IDs are machine-independent.
        doc.metadata["source"] = str(
            Path(doc.metadata["source"]).resolve().relative_to(root)
        )

    logger.info("Loaded %d documents from %s", len(docs), root)
    return docs


def _chunk_id(chunk: Document) -> str:
    key = f"{chunk.metadata.get('source')}|{chunk.metadata.get('start_index')}|{chunk.page_content}"
    return str(uuid.uuid5(_CHUNK_NAMESPACE, key))


def chunk_documents(
    docs: Sequence[Document], chunk_size: int = 1000, chunk_overlap: int = 150
) -> list[Document]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(list(docs))

    for chunk in chunks:
        chunk.metadata["chunk_id"] = _chunk_id(chunk)
        chunk.metadata["chunk_size"] = chunk_size
        chunk.metadata["chunk_overlap"] = chunk_overlap

    logger.info("Split into %d chunks (size=%d, overlap=%d)", len(chunks), chunk_size, chunk_overlap)
    return chunks


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #
def index_documents(
    data_dir: str | Path,
    collection_name: str = COLLECTION_NAME,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    batch_size: int = 128,
    reset: bool = False,
) -> int:
    require_openai_key()
    ensure_pgvector_extension()
    chunks = chunk_documents(load_documents(data_dir), chunk_size, chunk_overlap)
    if not chunks:
        logger.warning("No chunks produced; nothing to index.")
        return 0

    store = get_vector_store(collection_name=collection_name, reset=reset)

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        # Deterministic IDs -> re-running upserts instead of duplicating rows.
        store.add_documents(batch, ids=[c.metadata["chunk_id"] for c in batch])
        logger.info("Upserted %d/%d chunks", min(start + batch_size, len(chunks)), len(chunks))

    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk documents and index them into pgvector.")
    parser.add_argument("--data-dir", required=True, help="Directory containing .md/.txt files")
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--reset", action="store_true", help="Drop the collection before indexing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    n = index_documents(
        data_dir=args.data_dir,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        batch_size=args.batch_size,
        reset=args.reset,
    )
    logger.info("Done. Indexed %d chunks into collection '%s'.", n, args.collection)


if __name__ == "__main__":
    main()
