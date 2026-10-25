"""Run the RAG pipeline over the test set and score it with Ragas.

Metrics: faithfulness, answer relevancy, context precision, context recall.

Usage:
    python eval/evaluate_pipeline.py --testset eval/data/testset.jsonl --k 4
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)
from ragas.run_config import RunConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.indexer import COLLECTION_NAME, get_vector_store  # noqa: E402
from src.models import (  # noqa: E402
    DEFAULT_MAX_WORKERS,
    EMBEDDING_MODEL,
    JUDGE_MODEL,
    PROVIDER,
    RAG_MODEL,
    REQUEST_TIMEOUT,
    check_provider,
    get_chat_model,
    get_embeddings,
)

load_dotenv()
logger = logging.getLogger(__name__)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a precise assistant. Answer the question using ONLY the context below. "
            "If the context does not contain the answer, say you don't know.\n\n"
            "Context:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


def load_testset(path: str | Path) -> pd.DataFrame:
    if not Path(path).is_file():
        raise SystemExit(
            f"Test set not found at {path}. Run eval/generate_testset.py first."
        )
    df = pd.read_json(path, lines=True)
    missing = {"user_input", "reference"} - set(df.columns)
    if missing:
        raise ValueError(f"Test set is missing required columns: {missing}")
    return df


def run_rag(
    questions: list[str], k: int, model: str, collection_name: str, max_concurrency: int
) -> tuple[list[list[str]], list[str]]:
    """Retrieve contexts and generate answers for every question (batched)."""
    store = get_vector_store(collection_name=collection_name)
    retriever = store.as_retriever(search_kwargs={"k": k})
    cfg = {"max_concurrency": max_concurrency}

    retrieved = retriever.batch(questions, config=cfg)
    contexts = [[doc.page_content for doc in docs] for docs in retrieved]

    chain = RAG_PROMPT | get_chat_model(model) | StrOutputParser()
    inputs = [
        {"question": q, "context": "\n\n---\n\n".join(ctx)} for q, ctx in zip(questions, contexts)
    ]
    answers = chain.batch(inputs, config=cfg)
    return contexts, answers


def evaluate_pipeline(
    testset_path: str | Path,
    k: int = 4,
    rag_model: str = RAG_MODEL,
    judge_model: str = JUDGE_MODEL,
    collection_name: str = COLLECTION_NAME,
    max_concurrency: int = DEFAULT_MAX_WORKERS,
    output_dir: str | Path = ROOT / "eval" / "results",
) -> pd.DataFrame:
    check_provider(rag_model, judge_model, EMBEDDING_MODEL)
    testset = load_testset(testset_path)
    questions = testset["user_input"].tolist()
    logger.info("Running RAG pipeline on %d questions (k=%d, model=%s)", len(questions), k, rag_model)

    contexts, answers = run_rag(questions, k, rag_model, collection_name, max_concurrency)

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": q,
                "retrieved_contexts": ctx,
                "response": ans,
                "reference": ref,
            }
            for q, ctx, ans, ref in zip(questions, contexts, answers, testset["reference"])
        ]
    )

    metrics = [
        Faithfulness(),
        ResponseRelevancy(),                 # reported as "answer_relevancy"
        LLMContextPrecisionWithReference(),  # reported as "llm_context_precision_with_reference"
        LLMContextRecall(),                  # reported as "context_recall"
    ]

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=LangchainLLMWrapper(get_chat_model(judge_model)),
        embeddings=LangchainEmbeddingsWrapper(get_embeddings()),
        run_config=RunConfig(
            max_workers=max_concurrency, timeout=REQUEST_TIMEOUT, max_retries=10
        ),
        show_progress=True,
    )

    results_df: pd.DataFrame = result.to_pandas()
    metric_cols = [m.name for m in metrics]

    # Carry test-set metadata through so scores can be sliced by query type.
    if "synthesizer_name" in testset.columns:
        results_df["synthesizer_name"] = testset["synthesizer_name"].values

    # ---- Summary & persistence ------------------------------------------- #
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "testset": str(testset_path),
        "n_samples": len(results_df),
        "config": {"provider": PROVIDER, "k": k, "rag_model": rag_model,
                   "judge_model": judge_model, "embedding_model": EMBEDDING_MODEL,
                   "collection": collection_name},
        "scores": {c: float(results_df[c].mean()) for c in metric_cols},
        "nan_counts": {c: int(results_df[c].isna().sum()) for c in metric_cols},
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_df.to_csv(output_dir / f"eval_{stamp}.csv", index=False)
    (output_dir / f"summary_{stamp}.json").write_text(json.dumps(summary, indent=2))

    logger.info("Mean scores:\n%s", results_df[metric_cols].mean().round(4).to_string())
    if "synthesizer_name" in results_df.columns:
        logger.info(
            "Scores by query type:\n%s",
            results_df.groupby("synthesizer_name")[metric_cols].mean().round(4).to_string(),
        )
    logger.info("Results written to %s", output_dir)

    return results_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline with Ragas.")
    parser.add_argument("--testset", default=str(ROOT / "eval" / "data" / "testset.jsonl"))
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    parser.add_argument("--rag-model", default=RAG_MODEL)
    parser.add_argument("--judge-model", default=JUDGE_MODEL)
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--output-dir", default=str(ROOT / "eval" / "results"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    evaluate_pipeline(
        testset_path=args.testset,
        k=args.k,
        rag_model=args.rag_model,
        judge_model=args.judge_model,
        collection_name=args.collection,
        max_concurrency=args.max_concurrency,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
