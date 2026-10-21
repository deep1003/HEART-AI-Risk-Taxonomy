# HEART AI incident analysis

Snapshot: 21 October 2026.

This directory contains public, derived research outputs built from the OECD AI
Incidents Monitor, the AI Incident Database (AIID), and the MIT AI Incident
Tracker. The MIT tracker is an AIID-derived classification layer and is not
counted as an independent event source in `canonical_incidents_compact.json`.

## Files

- `downloads/source_records.csv.gz`: one row per source record using common
  fields and deduplication keys.
- `downloads/canonical_incidents_compact.json`: exact-ID-linked analytical
  event inventory.
- `downloads/incident_heart_edges_k5.csv.gz`: five HEART L4 candidates per
  event, with `in_k3` and `in_k5` flags.
- `downloads/duplicate_candidates.csv`: fuzzy candidates retained for review;
  none are automatically merged.
- `downloads/risk_network_nodes_k3.csv`: node centralities and communities.
- `downloads/risk_cooccurrence_edges_k3.csv`: raw and normalized projected ties.
- `downloads/network_metrics.json`: graph-level k=3 and k=5 diagnostics.
- `manifest.json`: hashes, source snapshots, licenses, and analytical grain.

## Interpretation boundary

The mappings are BGE-M3 cosine top-k candidates and have not been human
validated. Counts reflect public reporting and source curation, not incidence
rates or prevalence. Severity is not imputed when a source does not provide it.

