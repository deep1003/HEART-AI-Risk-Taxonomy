# About HEART content basis

The concise About page separates taxonomy construction from website exploration.
Content was checked against the designated HEART Technical Report local source
on 10 October 2026, without revising the report or its datasets.

Report version: `overleaf_master_algorithm_evaluation_20261010`, designated by
`OVERLEAF_MASTER.md` on 10 October 2026. Published PDF and the exact 57-file
Overleaf source ZIP are under `reports/`; their SHA-256 hashes are recorded in
`reports/release_20261010.json`. No report source or card dataset is revised here.

| About section | Basis |
| --- | --- |
| Why HEART | Report abstract, Introduction, Scope and Design Rationale |
| Data and structure | Methodology, Evidence Space and Corpus Construction; website release manifest |
| Taxonomy construction | Methodology, Semantic Representation and Clustering, Constrained Consolidation, EM-Style Constrained Assignment and Centroid Refinement |
| Algorithm 1/2 evaluation and key results | New Section 5.2, Tables 6 to 9; Algorithm 1 iterative consolidation only, Algorithm 2 fixed-reference agreement |
| Sensitivity and interpretation | Section 5.2 and Limitations; matched text, different encoder procedures, known L1, no held-out test or audited pair-level semantic ground truth |
| MIT appendix | Appendix C; related-corpus structural repeatability, 44 overlapping source titles, not fully independent semantic validation |
| Website exploration | `scripts/build_semantic_network.py`, `scripts/build_l3_colours.py`, `scripts/build_l4_colours.py`, `data/semantic_space_methods.md` |
| Keywords and applications mapping | `scripts/build_keyword_semantics.py`, `data/keyword_definitions.json`, `data/keyword_semantics.json`; application `SCENARIOS` and `match()` in `scripts/build_semantic_space.py`, published via `scripts/build_semantic_network.py` |
| How to use it | Current interface; report Application to an Urban Delivery-Robot Service, Context-Specific Taxonomy Composition and Intended Use |
| Limits | Report Limitations; current graph and filter method records |

The 82,971 construction records are not incidents or the downloadable card count.
The report's clustering and EM-style assignment are not presented as the live
graph algorithm. The website preserves approved categories and uses ForceAtlas2
for layout. No new claim of independent accuracy, causal validity or comparative
method superiority is introduced. Algorithm 2's 432/622 and 390/622 agreements
round to 69.45% and 62.70%. Historical F5 has 792 representatives, fresh BGE/E5
F5 has 817/875; these are explicitly distinguished. The 517/622 (83.12%) figure
is agreement between evaluator retrieval identities, not semantic accuracy.
Evaluation detail and filter-mapping detail remain independently collapsed.

The AI for Everyone example was checked against the current published membership:
295 cards, comprising 259 General and 36 Agentic cards; no Physical cards.
Its rule permits two L1 domains, matches category prefixes or English text terms,
then applies nine explicit exclusions. The linked 4 September 2026 Yonhap service
announcement was reopened on 10 October 2026. Capability-to-risk associations are
HEART's conditional analytical judgement, not claims of actual programme failures.
