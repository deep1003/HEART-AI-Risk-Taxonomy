# About HEART content basis

The concise About page separates taxonomy construction from website exploration.
Content was checked against the designated HEART Technical Report local source
on 11 October 2026, without revising the report or its datasets.

Report version: `overleaf_master_provenance_audit_20261011`, designated by
`OVERLEAF_MASTER.md` on 11 October 2026. Published PDF and the exact 57-file
Overleaf source ZIP are under `reports/`; their SHA-256 hashes are recorded in
`reports/release_20261011.json`. No report source or card dataset is revised here.
The previous 10 October release files and metadata are preserved unchanged.

| About section | Basis |
| --- | --- |
| Why HEART | Report abstract, Introduction, Scope and Design Rationale |
| Data and structure | Methodology, Evidence Space and Corpus Construction; website release manifest |
| Taxonomy construction | Methodology, Semantic Representation and Clustering, Constrained Consolidation, EM-Style Constrained Assignment and Centroid Refinement |
| Algorithm 1/2 evaluation and key results | Section 5.2; Algorithm 1 iterative consolidation only, Algorithm 2 fixed-reference agreement |
| Text/cache provenance and null restart diagnostic | Section 5.2, audit paragraphs and Table 9; confirmed text serialization/RNG reset, inferred intervals, unresolved median arithmetic |
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

## Provenance audit summary

The normalization-stage ordered text matches the cache filename prefix
`78d29c0cbe8d`; the later label snapshot has the same 1,612 ordered IDs and
bilingual definitions but changes 30 Korean labels and 19 English labels.
The vector-payload fingerprint also matches. Historical recorded BGE-M3 settings
are 256 tokens/batch 32, not the fresh 512 tokens/batch 8. No re-encoding is claimed.

The original resumable code resets seed-4 RNG on process start without saving RNG
state; the continuous replay carries RNG continuation. The audit's 406 contiguous
restart-segment diagnostics infer F1–F2, F3–F5, F6–F9, F10–F13, F14–F19,
F20–F27 and F28. These reproduce all 28 archived pass fractions, including the
six differences, but are not command-log-verified process boundaries. Counts and
thresholds are unchanged; the first fraction below 0.90 remains F15. Null draws
do not select the structural partition.

Maximum absolute median-z residual is approximately 1.65572 × 10^-5. Original
revision/weights, per-row execution and exact restart chronology remain
uncertified. Floating-point/BLAS/runtime causes are hypotheses. The exploratory
restart diagnostic does not change the strict original validator or saved traces.
Historical F5 retrieval still uses fresh embeddings of later representative text;
recovered cache wording does not retroactively change correspondence inputs.
These claims were checked against the reviewed TR source and audit JSON, not
inferred from the original publication. No new semantic validity is claimed.

The AI for Everyone example was checked against the current published membership:
295 cards, comprising 259 General and 36 Agentic cards; no Physical cards.
Its rule permits two L1 domains, matches category prefixes or English text terms,
then applies nine explicit exclusions. The linked 4 September 2026 Yonhap service
announcement was reopened on 10 October 2026. Capability-to-risk associations are
HEART's conditional analytical judgement, not claims of actual programme failures.
