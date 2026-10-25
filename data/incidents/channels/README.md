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

The overview starts with the 25 highest-degree nodes per domain plus the control-transfer card, retains the 240 strongest induced ties, and removes displayed isolates. The full view includes all active nodes and edges. Selecting a card preserves the graph layout and viewport, and opens a persistent right-hand incident panel with the source title, exact source summary, date, and original incident URL. The list switches between AIM and AIID and loads 15 entries at a time. Zooming in reveals full risk-name labels with collision-aware placement. Filtering never recomputes the reported full-network statistics.

L4 colors come directly from `data/semantic_space.json`. The same card has the same fill as in AI risk space, including semantic shades across L3 families. The domain legend uses the existing L1 anchor colors. Nodes are circles with white borders, and edges follow the existing quadratic-curve convention. A red outline identifies `A_INT_OVERSIGHT_003` without changing its fill.

Node area increases linearly with full-channel degree above a minimum area. Edge width increases with the square root of pair co-activation rate per 1,000 channel incidents. Both panels share these visual scales. The graphs are stacked vertically. The joint force layout uses a 1200-by-680 canvas, stronger repulsion, and a collision-separation pass with 22 extra coordinate units between overview node boundaries. Common cards retain shared coordinates for channel comparisons. Layout distances are not calibrated semantic, causal, or geographic distances.

## Files

- `networks.json` contains both complete aggregate networks, risk definitions, colors, full-network metrics, and display coordinates.
- `nodes.csv` contains degree and activation counts for all activated cards in each channel.
- `edges.csv` contains each card pair, its co-activation count, its per-1,000 rate, and cross-domain status.
- `validation.json` contains input hashes, counts, checks, seed, and rendering definitions.

The incident-detail assets contain titles and summaries from the existing public source-record release, with original database URLs and source attribution. Their title/description/AI-system hashes match every frozen mapping input. Underlying source article full texts and human-adjudication material are not exported.

## Linked incident details

```bash
python scripts/build_channel_incident_details.py --inputs /path/to/frozen/channel-inputs
```

This second script joins the existing public `source_records.csv.gz` to the paper’s frozen records by channel-specific ID. It asserts 12,200 exact title/description/AI-system hash matches and checks that every card’s list length equals its activation count. The generated `incidents-AIM.json` and `incidents-AIID.json` are fetched only when that source is selected. `incident_details_validation.json` records the input/output hashes and counts. Source descriptions are shown with source attribution, and all incident links retain their original OECD AIM or AIID URLs.

The right panel is reserved from the initial render. It initially displays an Overview with inventory counts, L1/L3 semantic color examples, and explanations of node size, curved links, the bridge ring, and zoom labels. Selecting a node replaces the Overview with its incidents without changing graph width. The Overview button restores the introduction.
