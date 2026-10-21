# HEART incident controls and robustness analysis

## Scope

This directory is a self-contained control and robustness analysis for 622 HEART L4 cards and 11,119 non-circular incident records. It does not modify the existing scale-law, incident-validation, embedding-ablation, website, or master-taxonomy outputs.

The fixed random seed is `20261021`. Proportion intervals use 2,000 nonparametric bootstrap replicates. Stratified incident-label tests use 2,000 permutations. Network label-shuffle tests use 1,000 permutations. Permutation p-values are reported as `(b + 1) / (B + 1)`.

## Inputs and invariants

The copied analysis inputs are under `inputs/`. Their SHA-256 hashes, row counts, model identifiers, and source repository commit are recorded in `00_input_audit/input_manifest.json`.

- HEART cards: 622 unique L4 cards, 55 L3 categories, 491 General, 68 Agentic, and 63 Physical cards.
- Primary incident correspondence: 11,119 incidents and 55,595 rank edges, exactly five candidate cards per incident. The analysis uses ranks 1 to 3 unless a robustness condition states otherwise.
- Incident text: title, description, and AI-system fields only.
- Embodied labels: 1,344 `embodied_rule` incidents and 253 `embodied_strong_external` incidents.
- Primary model: BGE-M3 digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`.
- Robustness model: `intfloat/multilingual-e5-base`, local revision `d128750597153bb5987e10b1c3493a34e5a4502a`.

Each stage requires the preceding stage to have a `PASS` checkpoint before it runs.

## Definitions

- **Home domain**: the L1 domain of the rank-1 mapped card.
- **Cross-domain incident**: at least two distinct L1 domains among the retained candidate cards.
- **Description network**: undirected L4 k-nearest-neighbour graph with `k=8` and cosine similarity at least `0.62`.
- **Incident coactivation network**: undirected L4 graph linking cards that co-occur among an incident's top-3 candidates.
- **Margin rule**: retains only candidate cards whose similarity is within delta of the rank-1 similarity.
- **Newman assortativity**: nominal assortativity by L1 domain label.
- **Observed/expected ratio**: observed cross-domain rate divided by the mean rate under the stated permutation null.

## Stages and outputs

1. `01_domain_size_controls/`
   - Home-domain by embodiment table with bootstrap intervals.
   - Home-domain-stratified permutation test.
   - HC3 logistic regression for `cross ~ embodied + C(home) + top1 similarity + rank1-rank3 gap`.
   - Card-definition retrieval baseline, margin-rule curves, General-card rarefaction, and matched non-embodied controls.
2. `02_network_label_shuffle/`
   - Common domain-label permutation baseline for the description and incident networks.
   - Observed cross-edge bootstrap intervals, null intervals, O/E, permutation p-values, and Newman assortativity.
3. `03_robustness/`
   - Repeats the core incident and network analyses with multilingual E5, Korean card text, and top-5 correspondence.
   - Applies the description-network homogeneity test to 1,835 MIT AI Risk Repository records across seven domains.
4. `04_agentic_evidence/`
   - MIT Tracker `behaviourType=Agent` incident count, cross-domain rate, stratified test, General-only cases, and word-level TF-IDF contrast.
   - Causal interpretation is intentionally left for human review.
5. `05_actor_counts/`
   - Unique alleged developer, deployer, and harmed-party counts by embodiment and cross-domain status.
   - Literal user versus explicit third-party mentions with bootstrap intervals. The `human_adjudication` field remains blank.
6. `06_centrality_uncertainty/`
   - Bootstrap rank intervals for residual description centrality and incident betweenness.
   - Bootstrap confidence interval for Spearman correlation between description degree and incident frequency.
   - Robust log-OLS and estimated-dispersion negative-binomial frequency models with an explicit model-comparison table.
7. `07_intro_cases/`
   - Source-verified metadata and non-circular top-3 mappings for AIID 1544, AIID 1740, and OECD AIM 2026-01-17-432f.
   - `human_verification` remains blank.

`summary.json` aggregates the stage checkpoints. `manuscript_key_numbers.csv` is the compact table intended for direct manuscript transfer. It separates observed proportions and their bootstrap intervals from permutation expectations and O/E ratios.

## Execution

Run all stages in sequence:

```bash
python code/run_controls.py --all
```

Run one stage after its predecessor has passed:

```bash
python code/run_controls.py --stage 3
```

Validate the completed package without displaying figures:

```bash
python code/validate_outputs.py
```

## Interpretation limits

- Cross-domain correspondence is a retrieval-based construct, not a human-adjudicated causal label.
- The primary BGE-M3 incident edges are treated as fixed inputs. E5 robustness uses a different multilingual representation and Korean card text, so absolute rates are not directly interchangeable.
- Card-count imbalance is addressed by stratification, regression, rarefaction, and matching, but these controls do not eliminate unobserved content differences.
- Matching uses top-1 similarity and text length only and does not establish causal effects of embodiment.
- The actor analysis depends on available alleged-role fields. Literal role coding is conservative and leaves ambiguous victim identity blank.
- AIID 1740 contains a documented disagreement about the chatbot's role. The table preserves that uncertainty and does not adjudicate it.
- Residual-centrality intervals resample description edges as a multiset; incident-betweenness intervals resample incidents. These quantify sampling sensitivity under the chosen constructions, not uncertainty in the underlying taxonomy definitions.
- The OLS model uses log-transformed frequency, whereas the negative-binomial model uses the count outcome. Coefficient direction and uncertainty are compared, but their AIC values are not treated as directly comparable.
- MIT domain labels and network thresholds are repository-specific ablation conditions and should not be interpreted as validation of HEART's three-domain ontology.
