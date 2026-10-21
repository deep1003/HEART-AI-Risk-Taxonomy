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

## Validation release

The `validation/` directory contains a non-circular remapping that excludes
source risk and harm labels from the embedding input. Those held-out labels are
used only for external checks.

- `human_validation_sample_150.csv`: frozen stratified adjudication sheet. It
  includes embodied incidents, but all human decision fields remain blank.
- `embodied_rule_audit_sample_100.csv`: frozen audit of strong-label and
  text-rule embodied candidates; human confirmation remains pending.
- `noncircular_incident_heart_edges_k5.csv.gz`: label-excluded k=5 remapping.
- `external_label_validation.csv`: checks against MIT, CSET and AIM labels.
- `bridge_analysis_k3_k5.csv`: semantic and incident-network bridge rankings.
- `hubness_residuals.csv`: raw degree and residual degree after controlling for
  semantic-centroid similarity and L1 fixed effects.
- `benign_intent_cases.csv`: rule-screened database-reported candidate cases.
- `validation_summary.json`: methods, principal estimates and limitations.

## Domain-control release

The `controls/` directory publishes compact results from the preregistered
domain-control and robustness analyses. It uses the non-circular incident
mapping above, the 622-card HEART master and seed `20261021`.

- `manuscript_key_numbers.csv`: principal estimates, intervals and tests.
- `01_home_domain_by_embodiment.csv`: home-domain and embodiment strata.
- `01_logistic_coefficients.csv`: adjusted cross-domain regression.
- `02_network_permutation_comparison.csv`: matched permutation tests for the
  description and incident-coactivation networks.
- `03_robustness_summary.json`: model, language and top-k robustness results.
- `07_case_verification_table.csv`: verified incident examples and candidate
  HEART mappings.
- `summary.json`: consolidated machine-readable results.
- `validation_report.json`: input-hash, count and output-integrity checks.

## Interpretation boundary

The mappings are BGE-M3 cosine top-k candidates. The 150-case human-validation
sheet and 100-case embodied-rule audit are prepared but **not adjudicated**.
Counts reflect public reporting and source curation, not incidence rates or
prevalence. Severity is not imputed when a source does not provide it.

