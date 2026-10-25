# Channel-specific reported-risk networks

The two networks reproduce the paper's frozen non-circular top-three mapping. OECD AIM is the primary channel with 10,449 incidents; AIID is the secondary channel with 1,751 incidents. AIM has 516 activated cards and 7,052 unique card-pair edges. AIID has 459 activated cards and 2,808 edges.

The estimand is the structure of candidate risks revealed in collected reports. Counts and network measures do not estimate population incidence, causality, or severity. The channels contain linked records and are not independent samples of all real-world harms.

## Inputs and reproduction

Use the frozen `channel_analysis_20261024/inputs/channel_edges_k5.csv.gz`, `channel_analytic_records.csv.gz`, and `01_channel_results/T1_revealed_network.csv`. Place the network metric CSV beside the two input files, then run from the site checkout with pandas, NumPy, and NetworkX installed.

```bash
python scripts/build_channel_incidents.py --inputs /path/to/frozen/channel-inputs
```

The seed is 20261021. Input hashes are recorded in `validation.json` and `networks.json`. The script asserts channel counts, unique candidate cards per incident, inventory identity, and agreement with the paper's graph outputs. The input records used here contain analytic metadata rather than incident narrative text.

## Calculation

For each incident, retain ranks 1–3 and form the three unordered pairs among its distinct candidate cards. Every unique pair forms an undirected edge, and repeated pairs increment its count. Degree is the number of distinct neighbors in the full channel graph. Cross-domain incident share counts records whose three cards cover at least two L1 domains. Cross-domain edge share counts unique edges joining different L1 domains. These are different denominators.

A revelation ratio divides a domain's share of card assignments by its share of the 622-card inventory. AIM contributes 31,347 assignments; AIID contributes 5,253. This ratio measures relative representation against inventory composition, not prevalence. Domain assortativity uses the unweighted network topology. Network O/E values are taken from the paper's 1,000 within-channel label permutations.

## Display

The overview starts with the 25 highest-degree nodes per domain plus the control-transfer card, retains the 240 strongest induced ties, and removes displayed isolates. The full view includes all active nodes and edges. The selected-card view shows up to 20 strongest neighbors per channel in a common circular arrangement. Filtering never recomputes the reported full-network statistics.

L4 colors come directly from `data/semantic_space.json`. The same card has the same fill as in AI risk space, including semantic shades across L3 families. The domain legend uses the existing L1 anchor colors. Nodes are circles with white borders, and edges follow the existing quadratic-curve convention. A red outline identifies `A_INT_OVERSIGHT_003` without changing its fill.

Node area increases linearly with full-channel degree above a minimum area. Edge width increases with the square root of pair co-activation rate per 1,000 channel incidents. Both panels share these visual scales. The joint force layout uses a fixed seed and a collision-separation pass. Common cards retain shared coordinates for channel comparisons. Layout distances are not calibrated semantic, causal, or geographic distances.

## Files

- `networks.json` contains both complete aggregate networks, risk definitions, colors, full-network metrics, and display coordinates.
- `nodes.csv` contains degree and activation counts for all activated cards in each channel.
- `edges.csv` contains each card pair, its co-activation count, its per-1,000 rate, and cross-domain status.
- `validation.json` contains input hashes, counts, checks, seed, and rendering definitions.

No incident text, personal source metadata, or human-adjudication material is included in these new assets. Historical downloads elsewhere in the website are not inputs to these graphs.
