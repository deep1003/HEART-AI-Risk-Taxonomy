# HEART

HEART is the **Hybrid Evidence-based AI Risk Taxonomy** for General, Agentic, and Physical AI.

This repository publishes the canonical L4 risk-card dataset and an English-first browser. Korean text is retained only where it is part of the official bilingual taxonomy: names, hierarchy labels, and risk definitions.

## Technical Report

The reviewed master of 10 October 2026 is available as the [42-page Technical Report](reports/HEART_Technical_Report_20261010.pdf) and its [verified 57-file LaTeX source bundle](reports/HEART_Technical_Report_20261010_source.zip). [About HEART](https://deep1003.github.io/HEART-AI-Risk-Taxonomy/about.html) summarises the algorithms, reference agreement, sensitivity and limitations, with technical details collapsed by default. [Release metadata](reports/release_20261010.json) records SHA-256 hashes.

Algorithm 1 is an iterative consolidation stage evaluation, not reproduction of the expert-rewritten 622-card set. Algorithm 2 evaluates agreement with expert assignments, not independent objective accuracy. MIT remains an appendix with source-overlap limitations. The published card datasets and golden reference were not changed by this report release.

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
