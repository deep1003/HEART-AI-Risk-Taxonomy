#!/usr/bin/env python3
"""Non-visual smoke tests for the incident-validation release."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/incidents/validation"

summary = json.loads((DATA / "validation_summary.json").read_text())
assert summary["canonical_incidents"] == 11119
assert summary["human_validation"]["sample_n"] == 150
assert summary["human_validation"]["status"] == "PENDING HUMAN ADJUDICATION"
assert summary["human_validation"]["embodied_rule_audit_n"] == 100
assert 0 < summary["incident_null"]["one_sided_p"] <= 0.001

sample = pd.read_csv(DATA / "human_validation_sample_150.csv", keep_default_na=False)
assert len(sample) == 150 and sample.canonical_incident_id.is_unique
assert sample.embodied_rule.astype(str).str.lower().eq("true").sum() >= 50
for field in ["top1_relevant", "top2_relevant", "top3_relevant", "reviewer_id", "adjudication_notes"]:
    assert field in sample and sample[field].eq("").all()

audit = pd.read_csv(DATA / "embodied_rule_audit_sample_100.csv", keep_default_na=False)
assert len(audit) == 100 and audit.canonical_incident_id.is_unique
assert audit.human_embodied_confirmed.eq("").all()

external = pd.read_csv(DATA / "external_label_validation.csv")
assert set(external.n) == {1752, 208, 10145}
bridges = pd.read_csv(DATA / "bridge_analysis_k3_k5.csv")
assert set(bridges.network) == {"semantic", "incident"} and set(bridges.k) == {3, 5}
hubs = pd.read_csv(DATA / "hubness_residuals.csv")
assert len(hubs) == 622 and hubs.L4_ID.is_unique
assert (DATA / "noncircular_incident_heart_edges_k5.csv.gz").stat().st_size > 500_000

page = (ROOT / "incidents.html").read_text()
for text in ["Human review is prepared, not completed", "52.3%", "p=0.0005",
             "No incident literally involving a microwave", "human_validation_sample_150.csv"]:
    assert text in page, text
assert (ROOT / "assets/incident-figures/embodied-null-validation.svg").stat().st_size > 1000
print("incident validation smoke tests: PASS")
