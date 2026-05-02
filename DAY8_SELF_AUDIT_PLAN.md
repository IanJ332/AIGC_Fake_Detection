# DAY 8 SELF-AUDIT AND HARDENING PLAN

**Generated**: 2026-05-02  
**Branch**: `main` @ `368daa1`  
**Auditor**: Research Agent + direct repo inspection

---

## 1. Repository Inspection Summary

### Files actually present (key findings)

| Component | Status | Notes |
| :--- | :--- | :--- |
| `requirements.txt` | ❌ MISSING | Referenced in `reproduce_all.sh` and README. Returns 404 on GitHub. |
| `corpus/manifest_100.csv` | ✅ Present | Contains `openalex_id`, `referenced_works`, `doi`, `pdf_url`, `citation_count` columns. **referenced_works is populated.** |
| `corpus/pdfs/` | ⚠️ 71 PDFs locally, 0 tracked in Git | Gitignored. 72 accessible (Data/); ~28 behind 403. |
| `corpus/raw_metadata/openalex_raw.jsonl` | ⚠️ Present locally, GITIGNORED | Should be inspected for citation data availability. |
| `src/query/operators.py` | ✅ Present | All 8 operators implemented. `citation_graph` returns limitation text. `multihop` is a placeholder. `quantitative` is corpus-wide only. |
| `eval/gold_answers.jsonl` | ⚠️ Present but weak | Contains `gold_answer_method` strings (query descriptions), NOT actual answer values. |
| `eval/questions_40.jsonl` | ✅ Present | 40 questions across all 8 tiers (5 per tier). |
| `scripts/reproduce_all.sh` | ⚠️ Incomplete | Calls `pip install -r requirements.txt` (missing file). Skips extraction. Eval-only. |
| `docs/` | ✅ Present | 10+ markdown docs. Reviewers flagged as potential "writeup" policy violation — see §4. |
| `artifacts/` | ✅ Present | Reports, manifests, samples committed. Good. |
| `Data/` | ✅ Locally present, gitignored | 330 MB total, all critical files present. |
| **`referenced_works` in manifest** | ✅ **KEY FINDING** | Full OpenAlex IDs for each paper's references are in `manifest_100.csv`. Citation graph IS buildable without re-fetching. |

---

## 2. Requirement-by-Requirement Compliance Table

| # | Requirement | Status | Evidence | Risk |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Specific research topic ~100 papers | ⚠️ PARTIAL | 100 in manifest, 72 PDFs parsed | MEDIUM |
| 2 | Full PDFs or download script | ❌ MISSING | PDFs gitignored, no download script exists | **BLOCKER** |
| 3 | Manifest with metadata + citation counts | ✅ | `corpus/manifest_100.csv` has all fields | LOW |
| 4 | Algorithm beyond basic RAG | ✅ | Operator-based DuckDB/Pandas pipeline | LOW |
| 5 | All 8 question tiers | ⚠️ PARTIAL | All scaffolded; citation_graph placeholder, multihop placeholder, quantitative generic | HIGH |
| 6 | No fine-tuning | ✅ | Zero LLM calls, fully deterministic | LOW |
| 7 | 40+ evaluation questions | ✅ | 40 questions, 5 per tier | LOW |
| 8 | Actual system outputs | ❌ MISSING | `system_output_path` in gold_answers.jsonl points to a file not in repo | HIGH |
| 9 | Quality-vs-budget curve (3 levels, actual reruns) | ❌ MISSING | `quality_vs_budget.md` describes planned ablations only | **BLOCKER** |
| 10 | Cost report | ✅ PARTIAL | $0 baseline documented; no measured higher-budget runs | MEDIUM |
| 11 | Reproducibility (clone → reproduce) | ❌ MISSING | No `requirements.txt`, no download script, eval-only `reproduce_all.sh` | **BLOCKER** |
| 12 | Cost cap ≤ $30 | ✅ | $0 spend documented | LOW |
| 13 | Cited, defensible answers with evidence | ⚠️ PARTIAL | Evidence collection works but citation_graph/multihop return stubs | MEDIUM |

---

## 3. Reviewer Feedback Classification

### Critic Agent 1

| Criticism | Classification | Rationale |
| :--- | :--- | :--- |
| Missing `requirements.txt` | ✅ **VALID BLOCKER** | Confirmed missing from repo. `reproduce_all.sh` calls it and would fail immediately. |
| Reproducibility needs private Data bundle | ✅ **VALID BLOCKER** | Fresh clone cannot run anything without a download script or data. |
| PDFs missing / no download script | ✅ **VALID BLOCKER** | Assessment explicitly allows download script. Not providing one is a gap. |
| Citation graph too shallow | ✅ **VALID, HIGH** | `manifest_100.csv` has `referenced_works` column with full OpenAlex IDs. Real graph is buildable. |
| Multihop is placeholder | ✅ **VALID, HIGH** | `answer_multihop` returns a static string; doesn't execute intersections. |
| Quantitative too generic | ✅ **VALID, MEDIUM** | Returns corpus totals for all questions; ignores `entities.csv` for entity-specific counts. |
| Gold answers too method-oriented | ✅ **VALID, MEDIUM** | Contains query descriptions, not computed expected values. |
| Evaluation measures routing, not correctness | ✅ **VALID, MEDIUM** | "40/40 operator success" = "CLI didn't crash", not answer accuracy. |
| Topic drift in manifest | ⚠️ **PARTIALLY VALID** | Manifest has `exclusion_reason` and `risk_flags` columns. May already be flagged; needs audit. |
| Delete `docs/` to avoid "writeup" rule | ❌ **NOT APPLICABLE** | See §3 Agent 2 analysis below. |

### Critic Agent 2

| Criticism | Classification | Rationale |
| :--- | :--- | :--- |
| "No Writeups" rule — delete `docs/` | ❌ **OVERCAUTIOUS / MISREAD** | The rule means "don't submit only a writeup instead of code." Day-plan docs (`day4_drive_notebook_plan.md`) are internal progress logs, not slides/marketing. Keep `docs/` but do not highlight it as the deliverable. |
| Execute budget ablations with real API spend | ⚠️ **PARTIALLY VALID** | The spirit requires showing the trade-off curve. However, **local BM25 or TF-IDF ablations at $0 are a valid alternative** to paid API runs. The assessment says "different budget levels," not "paid APIs only." Three $0-tier runs with different retrieval strategies can satisfy this. |
| Consolidate docs into README | ⚠️ **PARTIALLY VALID** | The README should be the primary navigation hub. Add pointers to docs, but don't delete them. |
| Complete corpus to exactly 100 PDFs | ⚠️ **PARTIALLY VALID** | Getting more PDFs is valuable. The user confirms they can re-run Colab notebooks to fetch more. This is now the user's primary objective. |

### Critic Agent 3

| Criticism | Classification | Rationale |
| :--- | :--- | :--- |
| PDF download script missing | ✅ **VALID BLOCKER** | Same as Agent 1. Assessment explicitly allows this path. |
| Quality-vs-budget curve not executed | ✅ **VALID BLOCKER** | Confirmed: `quality_vs_budget.md` is entirely "planned." |
| Citation graph (Tier 5) likely superficial | ✅ **VALID, HIGH** | But solvable: `referenced_works` column in manifest has full OpenAlex IDs. |
| Negation (Tier 7) may rely on heuristics | ⚠️ **PARTIALLY VALID** | Current implementation identifies "no result tuples" and "no method section." Extending to "no entity X" is feasible from `entities.csv`. |
| Evaluation doesn't compare against gold answers | ✅ **VALID, MEDIUM** | `gold_answers.jsonl` should contain computed expected values, not query descriptions. |
| `reproduce_all.sh` doesn't rebuild corpus end-to-end | ✅ **VALID, HIGH** | Eval-only mode is incomplete. Should at minimum have a `--rebuild` flag. |

---

## 4. Day 8 Hardening Plan

### Phase A: Must-Fix Compliance (BLOCKERS first)

**A1. Add `requirements.txt`**
- File: `requirements.txt` (NEW)
- Content: Pin exact dependencies from `pip freeze` in the working Colab environment.
- Difficulty: **S**
- Risk: LOW — without this, all scripts fail immediately.
- Validation: `pip install -r requirements.txt` completes without error.
- Commit: YES

**A2. Add `scripts/download_corpus.py`**
- File: `scripts/download_corpus.py` (NEW)
- Logic: Read `corpus/manifest_100.csv`, iterate `pdf_url` column, attempt download for each paper. Skip 403s gracefully, log a `download_report.txt` with success/failure per paper_id.
- This satisfies the assessment's "download script if PDFs exceed GitHub limits."
- Difficulty: **S** — `src/acquire/download_documents.py` already does most of this.
- Risk: LOW
- Validation: Run against manifest; confirm it downloads accessible PDFs.
- Commit: YES

**A3. Strengthen `scripts/reproduce_all.sh`**
- File: `scripts/reproduce_all.sh` (MODIFY)
- Add a `--download` flag that calls `download_corpus.py` first.
- Make the script self-contained: verify `requirements.txt` installed, verify `Data/` structure, optionally rebuild from PDFs, run eval.
- Difficulty: **S**
- Commit: YES

**A4. Add actual system outputs to repo**
- File: `artifacts/eval_outputs/day6_eval_outputs.jsonl` (NEW)
- Run `python eval/run_eval.py` locally, capture output to a JSONL file with question_id + full system answer.
- This gives reviewers real outputs to inspect without re-running.
- Difficulty: **S**
- Commit: YES (outputs are small text)

**A5. Implement quality-vs-budget curve (three measured modes)**
- File: `eval/run_budget_eval.py` (NEW), `docs/quality_vs_budget.md` (UPDATE)
- Three budget tiers (all $0, no paid API needed):
  - **Level 0 ($0)**: Current rule-based operators only.
  - **Level 1 ($0 + BM25)**: Replace keyword evidence retrieval in `evidence.py` with `rank_bm25` over `sections.jsonl`. Measure evidence coverage improvement.
  - **Level 2 ($0 + sentence-transformer)**: Use `sentence-transformers` (`all-MiniLM-L6-v2`, free/local) for semantic snippet retrieval. Measure evidence coverage improvement.
- Record routing accuracy, evidence coverage, and answer quality score (manual spot-check of 5 questions per tier).
- Plot: 3-point curve in `artifacts/budget_curve.png`.
- Difficulty: **M**
- Commit: Script + results + updated `quality_vs_budget.md`

---

### Phase B: Operator Depth

**B1. Implement real citation graph operator**
- File: `src/query/operators.py` (MODIFY: `answer_citation_graph`)
- **KEY INSIGHT**: `manifest_100.csv` already has a `referenced_works` column containing lists of OpenAlex IDs (e.g., `['https://openalex.org/W123', ...]`). The corpus papers' own OpenAlex IDs are in the `openalex_id` column.
- Algorithm:
  1. Build a set of corpus `openalex_id` values → `corpus_ids`.
  2. For each corpus paper, parse its `referenced_works` list.
  3. Find intersections: which corpus papers are cited by other corpus papers?
  4. Build an internal citation count per paper (how many other corpus papers cite it).
  5. Answer citation graph questions from this internal index.
- This requires no external API call and no re-extraction. All data is in `manifest_100.csv`.
- Difficulty: **M**
- Validation: `answer_citation_graph("Which papers are cited most within the corpus?", ...)` returns named papers with counts.

**B2. Implement real multihop entity intersection**
- File: `src/query/operators.py` (MODIFY: `answer_multihop`)
- Current stub: returns a static string.
- Real implementation: Parse question with regex to extract entity names → query `entities.csv` for paper_ids per entity → return intersections.
- Example: "Papers using GenImage AND AUC" → find `paper_ids` where entity=GenImage AND find `paper_ids` where entity=AUC → return intersection.
- Difficulty: **M**
- Validation: Q026 ("Papers using GenImage and AUC") returns non-empty named paper list.

**B3. Make quantitative operator question-specific**
- File: `src/query/operators.py` (MODIFY: `answer_quantitative`)
- Current: Always returns corpus totals (paper_count, result_count, avg).
- Real implementation: Parse question for entity name → count from `entities.csv`. Parse for "percentage" → compute from `paper_section_stats.csv`. Parse for "median" → compute from section stats.
- Difficulty: **S-M**
- Validation: Q037 ("How many papers mention GenImage?") returns the specific count, not total papers.

**B4. Extend negation operator for entity-specific absence**
- File: `src/query/operators.py` (MODIFY: `answer_negation`)
- Add: parse for entity name → find all paper_ids → return set difference (papers NOT mentioning that entity).
- Example: "papers without diffusion" → all paper_ids minus those with entity_type='generator_family', entity='diffusion'.
- Difficulty: **S**

---

### Phase C: Evaluation Credibility

**C1. Enrich `gold_answers.jsonl` with computed expected values**
- File: `eval/gold_answers.jsonl` (MODIFY)
- For computable questions (Q006, Q007, Q036, Q037, Q038, Q039, Q040), replace `gold_answer_method` with `gold_answer_value` computed from the actual local data.
- Example: Q039 "How many total entities?" → `"gold_answer_value": "15338"`.
- For non-computable questions (Q012 contradiction, Q022 citation graph), add a `gold_answer_criteria` (structural check).
- Difficulty: **S** — run a quick Python script to compute the values.

**C2. Add answer correctness check to `run_eval.py`**
- File: `eval/run_eval.py` (MODIFY)
- For questions with `gold_answer_value`, do a substring/numeric match check on system output.
- Report "exact match" count in addition to routing/execution.
- Difficulty: **S-M**

---

### Phase D: Corpus Quality

**D1. Audit and flag topic-drift papers in manifest**
- File: `corpus/manifest_100.csv` (MODIFY: add `scope_verdict` column)
- The manifest already has `exclusion_reason`, `risk_flags`, and `topic_family` columns. Run a targeted audit: find papers where `topic_family` is not in `{ai_generated_image_detection, face_forgery_detection, diffusion_detection, gan_detection}` and flag them.
- Do NOT delete from manifest; add `scope_verdict: in_scope / out_of_scope / borderline`.
- Difficulty: **S**
- Agent 1 cited "A Deep Learning Approach for Malnutrition Detection" and "Audio deepfakes: A survey." These should be flagged `out_of_scope` or `borderline`.

**D2. Re-run Colab notebooks to expand corpus (User's stated goal)**
- The user states they want to re-run all notebooks in Colab to fetch more papers and close the 72→100 PDF gap.
- This is separate from the hardening tasks above and should happen in parallel.
- When complete: update `Data/`, re-run extraction, re-run eval, update `artifacts/`.

---

## 5. Implementation Checklist

| Task | File(s) | Difficulty | Priority | Commit? | Validation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1: requirements.txt | `requirements.txt` | S | P0 | YES | `pip install -r requirements.txt` |
| A2: download_corpus.py | `scripts/download_corpus.py` | S | P0 | YES | Script runs, logs download results |
| A3: improve reproduce_all.sh | `scripts/reproduce_all.sh` | S | P0 | YES | Fresh clone + data → eval runs |
| A4: actual eval outputs | `artifacts/eval_outputs/day6_eval_outputs.jsonl` | S | P0 | YES | File exists, 40 entries |
| A5: budget eval + curve | `eval/run_budget_eval.py`, `docs/quality_vs_budget.md`, `artifacts/budget_curve.png` | M | P0 | YES | 3-point curve with measured numbers |
| B1: citation graph operator | `src/query/operators.py` | M | P1 | YES | Q022-Q025 return real paper names |
| B2: real multihop | `src/query/operators.py` | M | P1 | YES | Q026 returns intersection |
| B3: question-specific quantitative | `src/query/operators.py` | S-M | P1 | YES | Q037 returns GenImage count |
| B4: entity negation | `src/query/operators.py` | S | P1 | YES | Q034 returns papers without diffusion |
| C1: gold answer values | `eval/gold_answers.jsonl` | S | P1 | YES | Numeric fields added to 15+ questions |
| C2: correctness check in eval | `eval/run_eval.py` | S-M | P1 | YES | Report includes "exact match" count |
| D1: scope_verdict in manifest | `corpus/manifest_100.csv` | S | P2 | YES | All 100 rows have scope_verdict |
| D2: Colab re-run (user-driven) | Notebooks, then `Data/`, `artifacts/` | L | P2 | After run | 100 PDFs parsed |

---

## 6. Reviewer Advice Assessment: What NOT to Do

| Reviewer Suggestion | Decision | Reason |
| :--- | :--- | :--- |
| Delete `docs/` folder | **REJECT** | Rule is "don't submit ONLY a writeup." The docs are progress logs, not the deliverable. They provide context and transparency. |
| Spend real $1/$5/$20 on paid APIs | **MODIFY** | Use local free alternatives (BM25, sentence-transformers) as the $0 Level 1/2. This satisfies the spirit of the budget curve without unnecessary cost. |
| Rebuild corpus to exactly 100 | **ACCEPT (user-driven)** | The user will re-run Colab notebooks. This is the right path. |
| Replace gold_answers with exact values | **ACCEPT** | For computable questions, this is easy and significantly improves eval credibility. |

---

## 7. Final Recommendation

**Implement Day 8 hardening before submission.** The three hard blockers are:

1. **No `requirements.txt`** — causes immediate script failure on clone.
2. **No download script** — reviewer cannot build the corpus.
3. **No actual quality-vs-budget measurement** — explicitly required by the assessment.

The good news: all three are fixable in one day. The citation graph is also immediately buildable because `referenced_works` data is already in `manifest_100.csv` — this turns a "stub" tier into a real feature with zero additional API calls.

The user's goal of re-running Colab notebooks to increase PDF coverage from 72 to 100 is the right strategic move and should be done in parallel with the code hardening tasks above.

**Suggested execution order for Day 8:**
1. Add `requirements.txt` (15 min).
2. Add `scripts/download_corpus.py` (30 min).
3. Implement citation graph from manifest `referenced_works` (1 hr).
4. Implement real multihop intersections (1 hr).
5. Run budget eval at 3 levels + generate plot (2 hr).
6. Compute gold answer values and commit eval outputs (30 min).
7. Re-run Colab notebooks for expanded corpus (async, user-driven).
8. Update docs and push.
