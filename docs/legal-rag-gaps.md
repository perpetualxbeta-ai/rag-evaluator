# Applying rag-evaluator to legislation: learnings and gaps

This note records what we learned about using rag-evaluator on complex legal documents such as statutes, regulations and amendments, and what would need to change for real-world legal RAG.

**Summary:** rag-evaluator is a good benchmarking foundation, but its pipeline is built for short, self-contained documents. Legislation needs a structure-aware indexer in place of `src/indexer.py`, and retrieval upgraded from pure vector search to hybrid search with metadata filtering.

## Why the current setup struggles with legislation

### 1. Fixed-size chunking breaks context and references

`src/indexer.py` splits documents with LangChain's `RecursiveCharacterTextSplitter`, by character count (`--chunk-size 1000`, `--chunk-overlap 150` by default). It doesn't know about document structure.

Legal text depends on:

- **Cross-references**, such as "subject to section 4(b)(ii)".
- **Hierarchy:** title → chapter → section → subsection → paragraph.
- **Defined terms**, usually set out in a definitions section far from where they're used.

Character-based chunks can separate a definition from the clause that uses it, or cut a proviso off mid-sentence. Retrieval then returns a chunk that looks relevant but is missing the part that decides the answer.

### 2. Multi-hop reasoning across amendments

Legislation is rarely read in isolation. Acts are modified by later amending acts, schedules and regulations. Vector search ranks chunks only by semantic similarity to the question, so it can miss an older provision that's still in force, or an amendment that overrides the text it retrieved.

Our run on the sample corpus already showed this pattern at small scale. Questions that needed facts from two documents scored clearly lower than single-document ones (context recall 0.80 vs 0.93, faithfulness 0.54 vs 0.83 with `qwen2.5:3b`, k=4). In the worst case the warranty section wasn't retrieved at all, and the model gave a confident wrong answer. Legal corpora would make this much worse.

### 3. Limits of Ragas synthetic test generation

`eval/generate_testset.py` uses Ragas to generate questions automatically. For legal text:

- Ragas skips very short documents (under about 100 tokens), so short sections may never be tested.
- Dense, formal legal prose makes it harder to generate realistic multi-hop questions with correct reference answers.
- Small local models (we tried `llama3.2:3b` and `qwen2.5:3b`) couldn't complete generation at all on the sample corpus, failing Ragas's strict JSON output format.

For legal work, a hand-written or expert-reviewed test set is more reliable. See [Evaluating the fixes](#evaluating-the-fixes).

## Gaps to close for real-world legal RAG

### 1. Hierarchical, structure-aware parsing

**Gap:** chunking by character count ignores sections, numbering and nesting.

**Fix:** replace the splitter in `src/indexer.py` with a parser that:

- Splits on structural boundaries (headings, section numbers, nested lists) and keeps whole sections or subsections intact.
- Attaches hierarchical metadata to every chunk, for example:

  ```json
  {"act": "Income Tax Act", "part": "III", "section": "12", "subsection": "3(a)"}
  ```

- Optionally prepends the hierarchy path to the chunk text, such as "Income Tax Act > Part III > s.12(3)(a)", so the embedding captures where the text sits.

### 2. Hybrid search (keyword + vector)

**Gap:** pure vector search matches meaning, but legal questions often hinge on exact strings: section numbers, act names, case citations and defined terms.

**Fix:** combine pgvector similarity search with Postgres full-text search (`tsvector`, or BM25 via an extension), and merge the two result lists, for example with reciprocal rank fusion. Exact citations like "s.12(3)(a)" are then retrieved reliably, even when they're semantically similar to many other sections.

### 3. Graph-based retrieval for cross-references

**Gap:** vector search treats each chunk as independent. Phrases like "as defined in section 8" are never followed.

**Fix:** build a graph of relationships between sections, either as tables in the same Postgres database or as a separate graph store:

- Parent–child edges from the hierarchy.
- Explicit cross-reference edges, extracted from the text.
- "Defined term → definition" edges.

When section A is retrieved, also fetch the sections it references and the definitions of terms it uses.

### 4. Temporal versioning

**Gap:** legal questions are often time-specific, such as "What was the penalty for this offence in 2021, compared with 2026?" The current index has no idea which text was in force when.

**Fix:** store effective start and end dates on each chunk, and keep superseded versions instead of overwriting them. By default, filter retrieval to text in force today. When a question names a date, filter to the text in force on that date.

## Evaluating the fixes

rag-evaluator's job is to show whether each change helps. To use it for legal RAG:

1. **Build a legal test set.** Write 30–50 questions with reference answers, reviewed by someone who knows the law. Tag each with `synthesizer_name` so results split by type, for example `single_section`, `cross_reference`, `definition`, `amendment` and `point_in_time`. The evaluation script already reports scores per `synthesizer_name`.
2. **Record a baseline** with the current indexer and pure vector search.
3. **Change one thing at a time** (parser, then hybrid search, then graph expansion, then temporal filtering), re-index, re-run `eval/evaluate_pipeline.py`, and compare the summary JSONs. Context recall and context precision show retrieval improvements, and faithfulness shows whether answers stay grounded.
4. **Use a strong judge.** Legal answers turn on precise wording, and a small judge model adds noise that can hide real differences between runs. Use a larger model than the RAG model, ideally from a different model family.
