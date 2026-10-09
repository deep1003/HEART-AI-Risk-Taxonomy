# HEART semantic proximity network

The 622 canonical L4 cards and their 47 L3 assignments remain unchanged. Semantic space is the default home view, with a separate card-explorer tab.

## Reproduction and provenance

Install `scripts/semantic_requirements.txt` in a task-local environment and run `python scripts/build_semantic_network.py`, followed by `node scripts/test_semantic_space.cjs`. The older `build_semantic_space.py` is retained for historical lexical-projection reproduction and shared scenario rules, not as the current network builder.

`semantic_space.json` records the canonical source SHA-256, checked by the browser before rendering. `semantic_embeddings.npz` preserves 384-dimensional vectors, ordered IDs, model revision and text hash. Inference runs locally on CPU; card text is not sent to a hosted inference service.

## Current pipeline

1. Sort by L4 ID, concatenate the English name and definition, and encode using `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Mean pooling and L2 normalisation produce 384-dimensional embeddings. Input is limited to 256 word pieces; longer text is truncated. Korean translations are displayed but not encoded.
2. Retain the undirected union of eight nearest cosine neighbours per card at similarity >= 0.45. No artificial links are inserted. Edge weights are measured cosine similarity.
3. Weighted Louvain, resolution 1.0 and seed 23, produces 10 communities and 3,803 edges, one connected component and no isolates. Modularity 0.583259 describes graph partitioning, not classification accuracy.
4. A seeded weighted spring layout initialises ForceAtlas2, 350 iterations, scaling ratio 8, gravity 0.15, linlog attraction. Uniform centring and rescaling preserve all outliers without clipping. Filters never recompute positions.
5. Colours identify graph communities. Labels summarise dominant existing L3 names and do not reassign cards. Node radius scales with square-root graph degree, not severity, probability or EM confidence.

## Reference analysis

The supplied reference page, its live `assets/risk-space.js`, and local `scripts/build_semantic_proximity_network.py` were inspected. The historical implementation uses BGE-M3, seeded graph-regularised spherical EM, L3-profile similarity (0.65) plus direct semantic similarity (0.35), and ForceAtlas2. Its 54-community claim concerns a different release.

HEART reuses the node-link presentation, community colours, weighted connections and network layout, not stale IDs or old EM responsibilities. Current embeddings are recomputed from current HEART text. Links use direct embedding cosine only, and communities use Louvain, not EM. No taxonomy remapping is performed. Community totals are dependent on model and graph parameters, not validated counts of risk types.

## Interaction and limits

The four overlapping application lenses retain explicit editorial rules for delivery robots, factory humanoids, household assistant humanoids and autonomous network operations agents. These are conditional applicability filters, not empirically validated scenario labels. Scenario, community and keyword selections intersect. Inactive cards are pale or hidden; active nodes and the keyboard-accessible list open original cards. Community labels are clickable. Zoom and background dragging change only the viewport.

Links indicate semantic proximity, not causal propagation. Layout distances are not exact embedding distances. Community membership does not establish identical mechanisms, legal equivalence, probability or severity. No new risk cards, revised definitions, assignments or EM scores are generated. Encoder and threshold sensitivity has not been validated as classification accuracy.

## Technical sources

- [Sentence-transformer model and pooling](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Weighted Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html)
- [ForceAtlas2](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.forceatlas2_layout.html)
- [Reference visualisation](https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/risk-taxonomy-space.html)
