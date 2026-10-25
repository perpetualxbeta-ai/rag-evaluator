# rag-evaluator

An evaluation harness for retrieval-augmented generation (RAG) pipelines. It indexes a document corpus into Postgres with [pgvector](https://github.com/pgvector/pgvector), generates a synthetic question–answer test set with [Ragas](https://docs.ragas.io), and scores the pipeline on four metrics:

| Metric | Column in results | What it measures |
|---|---|---|
| Faithfulness | `faithfulness` | Whether the answer's claims are supported by the retrieved context (hallucination check) |
| Answer relevancy | `answer_relevancy` | Whether the answer addresses the question that was asked |
| Context precision | `llm_context_precision_with_reference` | Whether the relevant chunks are ranked near the top of the retrieved set |
| Context recall | `context_recall` | Whether the retrieved context contains everything needed for the reference answer |

## How it works

```
data/corpus/*.md|*.txt
        │
        ├──► src/indexer.py ──────────► pgvector (chunked + embedded)
        │                                      │
        └──► eval/generate_testset.py           │ retrieve top-k
                     │                          ▼
              eval/data/testset.jsonl ──► eval/evaluate_pipeline.py ──► eval/results/
                                           (answer with RAG_MODEL,        eval_<ts>.csv
                                            score with JUDGE_MODEL)       summary_<ts>.json
```

The test set is generated from the **raw documents**, not from your chunks. That keeps it fixed while you change chunk size, overlap or `k`, so runs with different configurations are directly comparable.

## Requirements

- Python 3.10–3.13
- Docker (or any Postgres 14+ with the `vector` extension available)
- **Either** [Ollama](https://ollama.com) for free local models, **or** an OpenAI API key

## Choosing a model provider

Set `LLM_PROVIDER` in `.env`:

| | `ollama` (default in `.env.example`) | `openai` |
|---|---|---|
| Cost | Free, runs on your machine | Pay per use (a 10-question run is well under $1) |
| Setup | Install Ollama and pull two models | API key from platform.openai.com |
| Speed | Minutes per run on a laptop | Fast, runs in parallel |
| Score reliability | Lower: small judges are noisier and sometimes produce unparseable output (`NaN` scores) | Higher |

Ollama is good for trying the repo and for iterating on chunking. For scores you'll report or compare over time, use a strong judge model.

Each provider gets its own pgvector collection (`rag_eval_ollama`, `rag_eval_openai`), because their embeddings have different dimensions. Switching providers never mixes indexes. Re-run the indexer after switching.

### Ollama setup

1. Install Ollama from [ollama.com](https://ollama.com) (on macOS: `brew install ollama`, or download the app) and start it.
2. Pull the default models (about 5 GB in total):
   ```bash
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
   On a machine with 8 GB of RAM, use a smaller model instead, e.g. `ollama pull llama3.2:3b`, and set `GENERATOR_MODEL`, `RAG_MODEL` and `JUDGE_MODEL` to it in `.env`.

## Setup

```bash
git clone https://github.com/perpetualxbeta-ai/rag-evaluator
cd rag-evaluator

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # set LLM_PROVIDER, and OPENAI_API_KEY if using OpenAI
```

Start Postgres with pgvector (on port 5433, to avoid clashing with any other Postgres on your machine):

```bash
docker run -d --name rag-evaluator-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5433:5432 pgvector/pgvector:pg16
```

The indexer creates the `rag` database and the `vector` extension automatically on first run.

## Usage

Put your `.md` and `.txt` files in a directory (e.g. `data/corpus/`), then run the three steps from the repo root.

### Quick start with the sample corpus

`data/sample_corpus/` contains seven short documents about a **fictional** warehouse-robot company (Halcyon Robotics and its Kestrel K2 robot): an overview, technical specs, safety procedures, a maintenance guide, warranty and support terms, firmware release notes, and an FAQ. The facts are invented and cross-referenced between documents (for example, the battery warranty depends on a state-of-health threshold defined in the maintenance guide and only reported from a specific firmware version), so Ragas can generate multi-hop questions and you can check any answer against the source files.

```bash
python -m src.indexer --data-dir data/sample_corpus --reset
python eval/generate_testset.py --data-dir data/sample_corpus --size 10
python eval/evaluate_pipeline.py --k 4
```

To use your own documents instead, replace `data/sample_corpus` with your directory in the commands below.

**1. Index the corpus**

```bash
python -m src.indexer --data-dir data/corpus --chunk-size 1000 --chunk-overlap 150
```

Chunk IDs are deterministic, so re-running upserts rather than duplicating rows. Add `--reset` when you change the chunk size, so chunks from the previous configuration are dropped.

**2. Generate a test set**

```bash
python eval/generate_testset.py --data-dir data/corpus --size 50
```

Writes `eval/data/testset.jsonl` (columns: `user_input`, `reference`, `reference_contexts`, `synthesizer_name`). Pass `--hf-dir eval/data/testset_hf` to also save it as a Hugging Face dataset. Commit the test set if you want every run to be scored against the same questions.

**3. Evaluate**

```bash
python eval/evaluate_pipeline.py --k 4
```

Writes per-question scores to `eval/results/eval_<timestamp>.csv` and averages to `summary_<timestamp>.json`, and logs the mean scores, broken down by query type.

You can also call it from Python to get the DataFrame directly:

```python
from eval.evaluate_pipeline import evaluate_pipeline

df = evaluate_pipeline("eval/data/testset.jsonl", k=6)
df.sort_values("faithfulness").head(10)   # worst answers first
```

### Comparing configurations

```bash
# Baseline
python -m src.indexer --data-dir data/corpus --chunk-size 1000 --reset
python eval/evaluate_pipeline.py --k 4

# Smaller chunks, more of them
python -m src.indexer --data-dir data/corpus --chunk-size 500 --chunk-overlap 75 --reset
python eval/evaluate_pipeline.py --k 8
```

To keep both indexes side by side instead of resetting, give each a different `--collection` in both commands.

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default (ollama / openai) | Used for |
|---|---|---|
| `LLM_PROVIDER` | `openai` if unset | Which provider supplies all models |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OPENAI_API_KEY` | — | OpenAI calls (only when `LLM_PROVIDER=openai`) |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` | pgvector connection (`.env.example` uses port 5433) |
| `PGVECTOR_COLLECTION` | `rag_eval_<provider>` | Collection name for the index |
| `EMBEDDING_MODEL` | `nomic-embed-text` / `text-embedding-3-small` | Indexing, retrieval and Ragas embeddings |
| `GENERATOR_MODEL` | `qwen2.5:7b` / `gpt-4o-mini` | Synthetic test set generation |
| `RAG_MODEL` | `qwen2.5:7b` / `gpt-4o-mini` | Answering questions (the pipeline under test) |
| `JUDGE_MODEL` | `qwen2.5:7b` / `gpt-4o` | Scoring with Ragas |

With OpenAI, the judge defaults to a stronger model than the pipeline, so the pipeline isn't grading its own answers. With Ollama all three roles share one model to keep memory use down; if your machine can run a larger model, set `JUDGE_MODEL` to it.

Before any model call, each script checks the provider is usable: that the API key is set, or that Ollama is running and the models are pulled (it prints the `ollama pull` commands you need).

## Project layout

```
rag-evaluator/
├── requirements.txt
├── .env.example
├── data/
│   └── sample_corpus/        # fictional documents for trying the pipeline
├── src/
│   ├── models.py             # provider switch: Ollama or OpenAI models
│   └── indexer.py            # load, chunk, embed, upsert into pgvector
└── eval/
    ├── generate_testset.py   # Ragas synthetic QA generation
    ├── evaluate_pipeline.py  # RAG run + Ragas scoring → pandas DataFrame
    ├── data/                 # generated test sets
    └── results/              # evaluation outputs (git-ignored)
```

## Notes

- **Pinned versions.** The code targets the Ragas 0.2/0.3 API and the LangChain 0.3 package family. Keep the pins in `requirements.txt` unless you are migrating.
- **Two Postgres drivers.** `langchain-postgres` requires psycopg 3 (hence `postgresql+psycopg://`). `psycopg2-binary` is used only to create the `vector` extension.
- **Fewer samples than requested.** Ragas skips very short documents (roughly under 100 tokens) during test set generation, and incomplete samples are dropped.
- **Cost and time.** Every run makes LLM calls for answering and judging each question. Start with `--size 10` while you're setting things up. With Ollama, expect test set generation and evaluation to take several minutes each on a laptop.
- **Small local models and test generation.** If `generate_testset.py` fails partway with output-parsing errors on Ollama, retry with a smaller `--size`, or set `GENERATOR_MODEL` to a larger model if your machine can run one.
- **`NaN` scores.** A metric can return `NaN` when the judge's output can't be parsed. The counts are reported under `nan_counts` in the summary JSON.
