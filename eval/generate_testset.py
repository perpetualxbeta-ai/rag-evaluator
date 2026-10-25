"""Generate a synthetic QA test set from the raw corpus with Ragas.

Usage:
    python eval/generate_testset.py --data-dir data/corpus --size 50
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig
from ragas.testset import TestsetGenerator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.indexer import EMBEDDING_MODEL, load_documents  # noqa: E402

load_dotenv()
logger = logging.getLogger(__name__)

GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gpt-4o-mini")


def generate_testset(
    data_dir: str | Path,
    testset_size: int = 50,
    output_path: str | Path = ROOT / "eval" / "data" / "testset.jsonl",
    hf_dir: str | Path | None = None,
    generator_model: str = GENERATOR_MODEL,
    embedding_model: str = EMBEDDING_MODEL,
    max_workers: int = 8,
) -> pd.DataFrame:
    # Use full documents, not our chunks: Ragas builds its own knowledge graph
    # and the test set should be independent of the chunking under evaluation.
    docs = load_documents(data_dir)
    if not docs:
        raise ValueError(f"No documents found in {data_dir}")

    generator_llm = LangchainLLMWrapper(ChatOpenAI(model=generator_model, temperature=0))
    generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=embedding_model))

    generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)

    testset = generator.generate_with_langchain_docs(
        docs,
        testset_size=testset_size,
        run_config=RunConfig(max_workers=max_workers, timeout=180, max_retries=10),
    )

    df = testset.to_pandas()
    before = len(df)
    df = df.dropna(subset=["user_input", "reference"]).reset_index(drop=True)
    if len(df) < before:
        logger.warning("Dropped %d incomplete samples.", before - len(df))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # JSONL preserves list columns (reference_contexts) without CSV escaping issues.
    df.to_json(output_path, orient="records", lines=True, force_ascii=False)
    logger.info("Wrote %d samples to %s", len(df), output_path)

    if hf_dir:
        Dataset.from_pandas(df).save_to_disk(str(hf_dir))
        logger.info("Saved Hugging Face dataset to %s", hf_dir)

    if "synthesizer_name" in df.columns:
        logger.info("Query type distribution:\n%s", df["synthesizer_name"].value_counts())

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic RAG test set with Ragas.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--output", default=str(ROOT / "eval" / "data" / "testset.jsonl"))
    parser.add_argument("--hf-dir", default=None, help="Optional: also save as a HF dataset")
    parser.add_argument("--model", default=GENERATOR_MODEL)
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    generate_testset(
        data_dir=args.data_dir,
        testset_size=args.size,
        output_path=args.output,
        hf_dir=args.hf_dir,
        generator_model=args.model,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
