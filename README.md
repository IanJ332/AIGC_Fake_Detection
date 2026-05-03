# Synthetic Media Forensics: Research Comprehension QA Engine

A deterministic, zero-cost question-answering system that reasons across a corpus of 100 research papers on Synthetic Media Forensics and AI-Generated Visual Content Detection — answering queries about datasets, models, contradictions, trends, citations, and more with cited, defensible evidence.

## Topic

**Synthetic Media Forensics and AI-Generated Visual Content Detection** — a coherent subfield of computer vision and media forensics concerned with detecting, attributing, and analyzing manipulated or generated visual media (including GANs, diffusion models, image forgery, copy-move, and deepfake detection).

* The corpus spans generated image detection, deepfake/face forgery detection, image manipulation detection, visual media forensics, and benchmarks.
* The topic is coherent because all papers address whether visual media is generated, manipulated, forged, or attributable to generative pipelines.
* The scope is broad enough to support a robust 100-paper corpus while maintaining strict analytical cohesion.

## Architecture Overview

The system uses an **operator-based analytical pipeline** — no LLM fine-tuning, no embeddings, no paid APIs:

1. **Ingest**: PDFs → parsed Markdown → structured section segments (JSONL).
2. **Extract**: Rule-based entity extraction (datasets, models, metrics, generators) and result-tuple parsing → CSV tables + DuckDB index.
3. **Route**: Regex-based intent classifier maps natural-language questions to one of 8 analytical tiers.
4. **Operate**: Tier-specific deterministic operators (Pandas/SQL) produce structured answers.
5. **Evidence**: Every answer includes traceable grounding — paper ID, section anchor, and text snippet.

```
User Question → Router → Operator (DuckDB/Pandas) → Evidence Collector → Cited Answer
```

### Question Tiers Handled

| Tier | Name | Example |
|:---|:---|:---|
| 1 | Single-document factual | "What architecture does P001 use?" |
| 2 | Corpus-level aggregation | "List every dataset used across the 100 papers." |
| 3 | Comparative / contradiction | "Which papers report conflicting results on GenImage?" |
| 4 | Temporal / evolution | "How has detection accuracy changed from 2020 to 2024?" |
| 5 | Citation-graph reasoning | "Which papers build on the GenImage benchmark?" |
| 6 | Multi-hop / compositional | "Find papers that use both CLIP and Accuracy." |
| 7 | Negation / absence | "Which standard benchmark is absent from the corpus?" |
| 8 | Quantitative computation | "How many papers mention GenImage?" |

## Setup

### Prerequisites
- Python 3.10+
- Google Colab (recommended) or any Linux/macOS/Windows environment

### Installation
```bash
git clone https://github.com/IanJ332/AIGC_Fake_Detection.git
cd AIGC_Fake_Detection
pip install -r requirements.txt
```

### Corpus

The 100 PDFs are not committed to Git (size limits). Use the download script:
```bash
python scripts/download_corpus.py --manifest corpus/manifest.csv --out-dir corpus/pdfs
```

> **Note:** Some PDFs (~28) are behind publisher paywalls. The download script logs these as known failures. The system operates on all successfully acquired papers and documents inaccessible ones.

The manifest is at [`corpus/manifest.csv`](corpus/manifest.csv) with columns: `id, title, authors, year, venue, citation_count, source_url, pdf_url`.

### Data Directory

The system reads extracted data from a configurable `--data-dir` path. For Colab, this is typically Google Drive:
```
{DATA_DIR}/
├── registry/manifest_100.csv
├── extracted/entities.csv, result_tuples.csv, paper_entity_summary.csv
├── sections/sections.jsonl
├── tables/table_candidates.jsonl
└── index/research_corpus.duckdb
```

## Usage

### Ask a Question (CLI)
```bash
python -m src.query.cli --data-dir ./Data --question "What are the top 10 datasets mentioned across the corpus?"
```

### Run Full Evaluation (40 questions, all 8 tiers)
```bash
python eval/run_eval.py --data-dir ./Data --questions eval/questions_40.jsonl
```

### Run Budget Ablation (3 levels)
```bash
python eval/run_budget_eval.py --data-dir ./Data --questions eval/questions_40.jsonl --out-dir artifacts/reports
```

### Reproduce End-to-End
```bash
bash scripts/reproduce_all.sh --eval-only ./Data   # default: evaluate on existing data
bash scripts/reproduce_all.sh --rebuild ./Data      # full: download PDFs, parse, extract, evaluate
```

### Colab Notebooks

The recommended workflow uses Google Colab with Google Drive as persistent storage:

| Notebook | Purpose |
|:---|:---|
| `01_data_sync_and_check` | Acquire PDFs, parse, segment sections |
| `02_small_batch_extraction_probe` | Validate extraction heuristics on a sample |
| `03_full_extraction_runner` | Full entity/result extraction → DuckDB |
| `04_qa_engine_runner` | Run QA engine + evaluation suite |
| `05_final_validation_runner` | Final validation: eval + budget + demo queries |

## Performance

- **Executable parsed corpus**: 117 papers
- **Entities**: 22,241
- **Result tuples**: 893
- **Routing Accuracy**: 95.0% (38/40 questions)
- **Operator Execution Success**: 100.0%
- **Evidence Coverage**: 92.5%
- **Spend**: $0.00
- **Branch/reproducibility**: main

## Cost Report

**Total spend: $0.00.** No paid APIs, no LLM calls, no embeddings. Purely deterministic operators on CPU. OpenAlex and OA backfill use no paid APIs.

| Level | Mode | Routing Accuracy | Operator Success | Evidence Coverage | Avg Latency | Spend |
|:---|:---|:---|:---|:---|:---|:---|
| 0 | router_only | 95.0% | 100.0% | 0.0% | 0.000s | $0.00 |
| 1 | operator_no_evidence | 95.0% | 100.0% | 0.0% | 0.165s | $0.00 |
| 2 | operator_with_evidence | 95.0% | 100.0% | 92.5% | 0.135s | $0.00 |

See [`docs/quality_vs_budget.md`](docs/quality_vs_budget.md) and [`docs/cost_report.md`](docs/cost_report.md) for details.

## Key Design Decisions

1. **No LLM in the loop** — avoids hallucination, cost, and latency. Every answer is traced to a DuckDB query or Pandas operation over extracted data.
2. **Operator-per-tier** — each question tier has a dedicated analytical operator optimized for that reasoning pattern.
3. **Citation graph from metadata** — uses OpenAlex `referenced_works` to build intra-corpus citation edges without parsing reference sections.
4. **Rule-based routing** — regex keyword classifier achieves 95% accuracy on the 40-question evaluation set; no ML model needed.

## Repository Structure

```
├── corpus/               # Manifest files (PDFs excluded from Git)
│   ├── manifest.csv      # 100-paper manifest (id, title, authors, year, venue, citation_count, source_url)
│   └── manifest_100.csv  # Full metadata manifest with OpenAlex fields
├── src/
│   ├── query/            # Router, operators, CLI, evidence collector
│   ├── extract/          # Entity and result extraction
│   ├── parse/            # PDF parsing and section segmentation
│   └── ingest/           # Corpus expansion utilities
├── eval/
│   ├── questions_40.jsonl      # 40 evaluation questions (all 8 tiers)
│   ├── gold_answers.jsonl      # Gold answers with derivation methods
│   ├── run_eval.py             # Evaluation runner
│   └── run_budget_eval.py      # Budget ablation runner
├── scripts/
│   ├── download_corpus.py      # PDF download script
│   └── reproduce_all.sh        # End-to-end reproduction
├── docs/                 # Cost report, quality-vs-budget, limitations
├── artifacts/            # Lightweight audit evidence (reports, samples, manifests)
└── notebooks/            # Colab notebooks (01–05)
```