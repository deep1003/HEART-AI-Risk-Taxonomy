# HEART semantic proximity network

The 622 canonical L4 cards and their 47 L3 assignments remain unchanged. Semantic space is the default home view, with a separate card-explorer tab.

## Reproduction and provenance

Install `scripts/semantic_requirements.txt` in a task-local environment and run `python scripts/build_semantic_network.py`, followed by `node scripts/test_semantic_space.cjs`. The older `build_semantic_space.py` is retained for historical lexical-projection reproduction and shared scenario rules, not as the current network builder.

`semantic_space.json` records the canonical source SHA-256, checked by the browser before rendering. `semantic_embeddings.npz` preserves 1,024-dimensional BGE-M3 vectors, ordered IDs, Ollama model digest and text hash. Inference runs locally using Apple Metal through Ollama 0.32.1; card text is not sent to a hosted inference service. Rebuilding the graph can reuse the published vectors without Ollama or another download. Fresh inference is implemented in `scripts/compare_bge_m3.py`.

## Current pipeline

1. Sort by L4 ID, concatenate the English name and definition, and encode using `BAAI/bge-m3`, packaged as Ollama `bge-m3:latest`. The pinned model digest is `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`. L2 normalisation produces 1,024-dimensional dense embeddings. Requests use `truncate=false`, without an added instruction. Korean translations are displayed but not encoded.
2. Retain the undirected union of eight nearest cosine neighbours per card at similarity >= 0.60. No artificial links are inserted. Edge weights are measured cosine similarity. This exploratory floor preserves the full top-eight graph: the observed minimum candidate score is 0.6218. It is not an expert-calibrated accuracy threshold. Higher floors of 0.65, 0.70 and 0.75 produce 1, 13 and 93 isolated nodes respectively.
3. Weighted Louvain using `networkx.algorithms.community.louvain_communities` in NetworkX 3.5, resolution 1.0 and seed 23, produces 9 communities and 3,807 edges, one connected component and no isolates. Modularity 0.562975 describes graph partitioning, not classification accuracy. Link weights are cosine similarity, calculated as the dot product of L2-normalised vectors: w(i,j) = e(i) · e(j). Louvain is an algorithm name; 3.5 is the implementation library version, not an algorithm version.
4. A seeded weighted spring layout initialises ForceAtlas2, 350 iterations, scaling ratio 8, gravity 0.15, linlog attraction. Uniform centring and rescaling preserve all outliers without clipping. Filters never recompute positions.
5. Colours identify graph communities. Labels summarise dominant existing L3 names and do not reassign cards. Node strength is the sum of published incident cosine weights. Node area is linearly scaled over the full-network strength range to radii 3 to 15 display pixels: r = sqrt(9 + 216 × (strength − min)/(max − min)). Equal-strength networks use the midpoint area. Sizes remain fixed across filters, including pale inactive nodes. This is not severity, probability or EM confidence.

## Reference analysis

The supplied reference page, its live `assets/risk-space.js`, and local `scripts/build_semantic_proximity_network.py` were inspected. The historical implementation uses BGE-M3, seeded graph-regularised spherical EM, L3-profile similarity (0.65) plus direct semantic similarity (0.35), and ForceAtlas2. Its 54-community claim concerns a different release.

HEART reuses the node-link presentation, community colours, weighted connections and network layout, not stale IDs or old EM responsibilities. Current embeddings are recomputed from current HEART text. Links use direct embedding cosine only, and communities use Louvain, not EM. No taxonomy remapping is performed. Community totals are dependent on model and graph parameters, not validated counts of risk types.

## Interaction and limits

The three overlapping application lenses retain explicit editorial rules for delivery robots, household assistant humanoids and AI for Everyone (Korea). The factory-humanoid lens was removed from publication on 10 October 2026; its cards remain unchanged. These are conditional applicability filters, not empirically validated scenario labels. Scenario, community and keyword selections intersect. Inactive cards are pale or hidden; active nodes and the keyboard-accessible list open original cards. Community labels are clickable. Zoom and background dragging change only the viewport.

The AI for Everyone lens replaces autonomous network operations agents on 10 October 2026. Its service scope is based on [Yonhap News reporting of announced plans, 4 September 2026](https://www.yna.co.kr/view/AKR20260904048352017): domestic general-purpose chatbots, public and specialised digital agents, information search and delegated applications, bookings and payments via familiar channels. The English label is a descriptive translation, not a verified official name. The unrelated AI learning/development growth-ladder programme is not included. Exact deterministic inclusion/exclusion rules are in `SCENARIOS` in `scripts/build_semantic_space.py`. General and Agentic cards concerning reliability, privacy, harmful output, inclusion and delegated action are included conditionally; Physical-domain cards and explicitly excluded embodied/advanced-autonomy cases are not. These associations are our analytical inference from service capabilities, not claims made by the article or evidence of programme failures.

Links indicate semantic proximity, not causal propagation. Layout distances are not exact embedding distances. Community membership does not establish identical mechanisms, legal equivalence, probability or severity. No new risk cards, revised definitions, assignments or EM scores are generated. Encoder and threshold sensitivity has not been validated as classification accuracy.

## Technical sources

- [BGE-M3 model](https://huggingface.co/BAAI/bge-m3)
- [Ollama BGE-M3 package and embedding API](https://ollama.com/library/bge-m3)
- [Weighted Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html)
- [ForceAtlas2](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.forceatlas2_layout.html)
- [Reference visualisation](https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/risk-taxonomy-space.html)
# Display baseline

The default 100% zoom uses a 1.10 display multiplier, equivalent to the previous 110% view. Fit network restores this baseline. Weighted-degree radii remain unchanged in graph coordinates; displayed diameters are 6.6–33 pixels at the new default. Pointer hit testing uses the same multiplier.

## Model change record

On 9 October 2026, BGE-M3 replaced all-MiniLM-L6-v2 (384 dimensions, sentence-transformers 5.1.1, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`). All 622 inputs and approved L3 assignments are unchanged. Top-eight same-L3 agreement increases from 37.62% to 40.55%, but this is a diagnostic rather than semantic accuracy. Mean neighbour overlap is 47.39%; mixed qualitative examples remain. MiniLM vectors, graph and methods are preserved locally in `evidence_work/minilm_baseline_20261009/` and in the preceding Git history. The change is user-approved, not evidence that BGE-M3 is universally superior.
