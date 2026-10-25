# HEART

HEART is the **Hybrid Evidence-based AI Risk Taxonomy** for General, Agentic, and Physical AI.

This repository publishes the canonical L4 risk-card dataset and an English-first browser. Korean text is retained only where it is part of the official bilingual taxonomy: names, hierarchy labels, and risk definitions.

## Technical Report

The current master is the [36-page proofread Technical Report](reports/HEART_Technical_Report_20261014.pdf) (14 October 2026), with its [LaTeX source bundle](reports/HEART_Technical_Report_20261014_source.zip) and [release metadata](reports/release_20261014.json). It is synchronized with the Overleaf master and revises the specialist-proofread edition in American English and scientific style, refines the logical flow, condenses the Limitations and Future Directions section, attributes the six-step application-profile procedure to KT's AI impact assessment procedure (Park et al., 2025), and states that the delivery-robot example is illustrative and neither confirmed nor exhaustive. No evaluation score or card was changed. [About HEART](https://deep1003.github.io/HEART-AI-Risk-Taxonomy/about.html) summarizes the current methods and results. The previous [37-page specialist-proofread edition](reports/HEART_Technical_Report_20261011_compact_review.pdf) and its [source](reports/HEART_Technical_Report_20261011_compact_review_source.zip), the [39-page focused edition](reports/HEART_Technical_Report_20261011_focused_review.pdf), its [source](reports/HEART_Technical_Report_20261011_focused_review_source.zip), the earlier [37-page reference-reviewed edition](reports/HEART_Technical_Report_20261011_reference_review.pdf), its [source](reports/HEART_Technical_Report_20261011_reference_review_source.zip), the [provenance-audited PDF](reports/HEART_Technical_Report_20261011.pdf), its [source](reports/HEART_Technical_Report_20261011_source.zip), and all previous release files remain unchanged; the [reference-review record](reports/REFERENCE_REVIEW_20261011.md) describes an earlier edition.

Algorithm 1 is an iterative consolidation stage evaluation, not reproduction of the expert-rewritten 622-card set. Algorithm 2 evaluates agreement with expert assignments, not independent objective accuracy. The MIT check remains in the independent experiment package; its removed TR appendix is archived but not compiled. Source-overlap limitations remain. The published card datasets and golden reference were not changed by this report release.

## Dataset

The release contains 622 active L4 risk cards across 55 L3 categories:

- General AI: 491 cards
- Agentic AI: 68 cards
- Physical AI: 63 cards

Each card contains a stable L4 identifier, bilingual name and definition, L1 to L3 hierarchy, optional Facet and Act-type attributes, an evidence reference, and a direct quotation. Probability and Severity are reserved fields and intentionally remain blank.

## Files

- `data/heart_l4_risk_cards.csv`: canonical flat dataset
- `data/heart_l4_risk_cards.json`: website data
- `data/HEART_L4_Risk_Cards.xlsx`: formatted workbook
- `data/data_dictionary.csv`: field definitions
- `data/manifest.json`: counts and checksums
- `data/scale_law_diagnostics.json`: reproducible L4 degree and weighted-degree tail diagnostics
- `data/scale_law_top_l4.csv`: all L4 cards ranked by semantic connectivity and cross-domain share
- `source_snapshot/`: preserved inputs used to build this release

## Build

```bash
python3 scripts/build_heart_dataset.py
```

The build performs one-to-one L4 ID matching between the hierarchy masters and the evidence ledger, rejects duplicate identifiers, verifies required fields, checks L3 consistency, and keeps Probability and Severity blank.
# Semantic embedding release

The current semantic network uses BGE-M3 dense embeddings, 1,024 dimensions, served locally by Ollama 0.32.1. Model digest and source checksums are recorded in `data/semantic_space.json`. Its 3,807 cosine-weighted links and coordinates are unchanged. Solid per-L4 colours vary semantically within 55 human-approved L3 categories and three L1 anchors; neighbouring L3 colours are blended without changing assignments. Weighted Louvain (NetworkX 3.5) yields 9 diagnostic communities retained as metadata, not displayed colour groups. Darker colours do not mean higher risk. See `data/semantic_space_methods.md` for parameters, reproducibility and the previous MiniLM comparison.

## L4 scale-law diagnostics

[`scale-law-diagnostics.html`](scale-law-diagnostics.html) evaluates whether the L4 semantic graph has a statistically defensible power-law tail. The deterministic builder performs maximum-likelihood tail fitting, Kolmogorov-Smirnov cutoff selection, 1,000 semi-parametric bootstrap checks, and comparison with a lower-truncated lognormal alternative. It also publishes Top-5 and Top-10 L4 connectivity views with General, Agentic, and Physical AI neighbour composition. The analysis is descriptive of semantic-network structure and is not a probability, severity, impact, or regulatory-priority score.

```bash
python3 scripts/build_scale_law_diagnostics.py
python3 scripts/test_scale_law_diagnostics.py
```

## Current L3 definitions

The current bilingual definitions of all 55 L3 categories are synchronized with the root Appendix A of the Overleaf Technical Report as downloaded on 25 October 2026. The explorer and card details share `data/heart_l3_categories.json`. A CSV export and `data/l3_definitions_manifest.json` provide the complete catalog and source checksum. Category IDs, hierarchy, all 622 L4 cards, computed semantic positions, evaluation inputs and incident data remain unchanged. Historical releases retain their original definitions.
