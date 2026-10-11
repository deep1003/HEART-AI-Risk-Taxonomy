# HEART

HEART is the **Hybrid Evidence-based AI Risk Taxonomy** for General, Agentic, and Physical AI.

This repository publishes the canonical L4 risk-card dataset and an English-first browser. Korean text is retained only where it is part of the official bilingual taxonomy: names, hierarchy labels, and risk definitions.

## Technical Report

The current master is the [37-page specialist-proofread Technical Report](reports/HEART_Technical_Report_20261011_compact_review.pdf), with its [LaTeX source bundle](reports/HEART_Technical_Report_20261011_compact_review_source.zip) and [release metadata](reports/release_20261011_compact_review.json). It preserves the abstract, Introduction and Chapter 3 of the focused edition while compressing selected sections, clarifying F5 and evaluation metrics, and removing the compiled MIT appendix. [About HEART](https://deep1003.github.io/HEART-AI-Risk-Taxonomy/about.html) summarises the current methods and results with technical details collapsed by default. Some full-text and paid standards-clause checks remain limited; the [earlier reference-review record](reports/REFERENCE_REVIEW_20261011.md) describes an earlier edition, not a new complete audit. No evaluation score or card was changed. The [39-page focused edition](reports/HEART_Technical_Report_20261011_focused_review.pdf), its [source](reports/HEART_Technical_Report_20261011_focused_review_source.zip), the earlier [37-page reference-reviewed edition](reports/HEART_Technical_Report_20261011_reference_review.pdf), its [source](reports/HEART_Technical_Report_20261011_reference_review_source.zip), the [provenance-audited PDF](reports/HEART_Technical_Report_20261011.pdf), its [source](reports/HEART_Technical_Report_20261011_source.zip), and all previous release files remain unchanged.

Algorithm 1 is an iterative consolidation stage evaluation, not reproduction of the expert-rewritten 622-card set. Algorithm 2 evaluates agreement with expert assignments, not independent objective accuracy. The MIT check remains in the independent experiment package; its removed TR appendix is archived but not compiled. Source-overlap limitations remain. The published card datasets and golden reference were not changed by this report release.

## Dataset

The release contains 622 active L4 risk cards across 47 L3 categories:

- General AI: 492 cards
- Agentic AI: 67 cards
- Physical AI: 63 cards

Each card contains a stable L4 identifier, bilingual name and definition, L1 to L3 hierarchy, optional Facet and Act-type attributes, an evidence reference, and a direct quotation. Probability and Severity are reserved fields and intentionally remain blank.

## Files

- `data/heart_l4_risk_cards.csv`: canonical flat dataset
- `data/heart_l4_risk_cards.json`: website data
- `data/HEART_L4_Risk_Cards.xlsx`: formatted workbook
- `data/data_dictionary.csv`: field definitions
- `data/manifest.json`: counts and checksums
- `source_snapshot/`: preserved inputs used to build this release

## Build

```bash
python3 scripts/build_heart_dataset.py
```

The build performs one-to-one L4 ID matching between the hierarchy masters and the evidence ledger, rejects duplicate identifiers, verifies required fields, checks L3 consistency, and keeps Probability and Severity blank.
# Semantic embedding release

The current semantic network uses BGE-M3 dense embeddings, 1,024 dimensions, served locally by Ollama 0.32.1. Model digest and source checksums are recorded in `data/semantic_space.json`. Its 3,807 cosine-weighted links and coordinates are unchanged. Solid per-L4 colours vary semantically within 47 human-approved L3 categories and three L1 anchors; neighbouring L3 colours are blended without changing assignments. Weighted Louvain (NetworkX 3.5) yields 9 diagnostic communities retained as metadata, not displayed colour groups. Darker colours do not mean higher risk. See `data/semantic_space_methods.md` for parameters, reproducibility and the previous MiniLM comparison.
