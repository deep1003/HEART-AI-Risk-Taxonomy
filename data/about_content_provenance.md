# About HEART content basis

The results-focused About page follows the current reviewed Technical Report,
`overleaf_master_compact_review_20261011`, and the published exploration data.
The article removes report-download links and compresses the preceding version
from 1,117 to 518 words, including collapsed details. Report files, evaluation
results and risk-card data are unchanged. Earlier masters and the frozen expert
reference are preserved.

| About section | Basis |
| --- | --- |
| Purpose, 622 cards and 55 categories | Report abstract, Introduction and taxonomy methodology; website release manifest |
| Taxonomy construction | Methodology, Semantic Representation and Clustering, Constrained Consolidation, EM-Style Constrained Assignment and Centroid Refinement |
| Algorithm 1/2 evaluation and key results | Section 5.2; Algorithm 1 iterative consolidation only, Algorithm 2 fixed-reference agreement |
| Sensitivity and interpretation | Section 5.2 and Limitations; matched text, different encoder procedures, known L1, no held-out test or audited pair-level semantic ground truth |
| Website exploration | `scripts/build_semantic_network.py`, `scripts/build_l3_colours.py`, `scripts/build_l4_colours.py`, `data/semantic_space_methods.md` |
| Keywords and applications mapping | `scripts/build_keyword_semantics.py`, `data/keyword_definitions.json`, `data/keyword_semantics.json`; application `SCENARIOS` and `match()` in `scripts/build_semantic_space.py`, published via `scripts/build_semantic_network.py` |
| How to use it | Current interface; report Application to an Urban Delivery-Robot Service, Context-Specific Taxonomy Composition and Intended Use |
| Limits | Report Limitations; current graph and filter method records |

The 82,971 construction records are not incidents or the downloadable card count.
The report's clustering and iterative assignment are not the live graph algorithm.
The website preserves approved categories and uses ForceAtlas2 for layout.
For the 55-category release, Algorithm 2 achieves 65.11% Top-1 and 84.41% Top-3 agreement with the expert reference using BGE-M3.
Original F5 has 792 representatives, followed by expert rewriting into 622 cards;
semantic proximity is not verified equivalence or an optimal stopping criterion.
The concise article retains the model/input sensitivity and original-encoding
verification caveats, without intermediate audit output or local filenames.

The AI for Everyone example was checked against the current published membership:
295 cards, comprising 259 General and 36 Agentic cards; no Physical cards.
Its rules permit two L1 domains, match category prefixes or English text terms,
then apply explicit exclusions. The existing linked Yonhap service announcement
supports the stated capabilities. Capability-to-risk associations are HEART's
conditional analytical judgement, not claims of actual programme failures.

Method and mapping details remain independently collapsed by default. Keyword
thresholds are retrieval settings, separate from network-link thresholds and not
validated accuracy estimates. No new claim of independent accuracy, causality,
risk priority, certification or comparative superiority is introduced.
Report-download assets remain available in the repository even though their
links are removed from the About article.
