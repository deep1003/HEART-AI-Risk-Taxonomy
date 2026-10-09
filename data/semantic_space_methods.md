# HEART semantic-space explorer

The space reads the unchanged canonical `heart_l4_risk_cards.json`. Every point is an existing L4 ID. The generated JSON contains the exact source SHA256, coordinates, communities, keyword membership and neighbour edges. A source-hash mismatch disables this view rather than displaying a stale projection.

## Text geometry

The English name is included twice and the English definition once. The builder removes common English and repetitive risk-framing words, retains unigrams and bigrams occurring in at least two cards and at most 75% of cards, applies sublinear term frequency and smoothed inverse document frequency, and L2-normalises each row. A centred PCA representation retains 48 dimensions. Cosine t-SNE produces the two-dimensional display, with perplexity 35, 1,200 iterations and seed 23. Twelve k-means communities are constructed in the 48-dimensional space and named with their three highest-weight unigram terms.

This is a lexical semantic space, not a contextual neural embedding. t-SNE emphasises local neighbourhoods. Global separation, cluster area, density and axis values must not be interpreted as risk severity, incidence, probability or validated semantic boundaries. Clustering is an exploration layer and does not reassign the master taxonomy. The generated neighbourhood trustworthiness diagnostic assesses projection fidelity, not correct risk classification.

Edges represent up to three nearest other cards with TF-IDF cosine similarity at least 0.30. They are shown only for focused subsets of at most 150 active cards. They do not indicate causal relationships or risk propagation.

## Application communities

Four overlapping editorial lenses represent delivery robot services, factory humanoids, household assistant humanoids and autonomous network operations agents. Explicit ID membership and the limited prefix-based network-agent scope are preserved in `scripts/build_semantic_space.py`. Application membership describes potential relevance conditional on capabilities and deployment, not that every listed harm occurs in every system. Examples include robot navigation and pedestrian access, industrial manipulation and worker monitoring, household manipulation and intimate-space privacy, and agent authority, tools, correction and multi-agent coordination in network operations. Workplace-only monitoring is not assigned to the domestic lens.

The twelve keyword filters combine explicit category membership with documented mechanism terms. Choosing a scenario, text-derived community and keyword applies their intersection. A point has the same coordinates before and after filtering. Inactive points can remain as pale context or be hidden. Selecting an active point or keyboard-accessible list entry opens the existing card, without adding a card, changing its definition, or displaying EM scores.

## Reproduction

Install the pinned packages in a task-specific virtual environment, then run `python scripts/build_semantic_space.py`. Run `node scripts/test_semantic_space.cjs` to verify identities, scenario membership, all keyword intersections, coordinate validity and source preservation. The canonical card file is read-only throughout this process. Record runtime versions from the generated method metadata; floating-point results can differ slightly across numerical backends.

## Method references

- TF-IDF text features: https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction
- t-SNE and interpretation: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html
- Projection trustworthiness: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.trustworthiness.html

This release adds an exploratory view only. It does not promote the separate, unfinished evidence-revision dataset to the golden master.
