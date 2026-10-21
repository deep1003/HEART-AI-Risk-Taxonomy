#!/usr/bin/env python3
"""Independent integrity and publication checks for L4 scale-law diagnostics."""

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
space_bytes = (DATA / "semantic_space.json").read_bytes()
cards_bytes = (DATA / "heart_l4_risk_cards.json").read_bytes()
space = json.loads(space_bytes)
cards = json.loads(cards_bytes)
result = json.loads((DATA / "scale_law_diagnostics.json").read_text())

assert len(cards) == 622 == len(space["points"]) == result["node_count"]
assert len({card["L4_ID"] for card in cards}) == 622
assert len(space["clusters"]) == 55
assert len(space["edges"]) == result["edge_count"] == 3807
assert result["source"]["semantic_space_sha256"] == hashlib.sha256(space_bytes).hexdigest()
assert result["source"]["risk_cards_sha256"] == hashlib.sha256(cards_bytes).hexdigest()

degrees = {point["id"]: 0 for point in space["points"]}
strengths = {point["id"]: 0.0 for point in space["points"]}
cards_by_id = {card["L4_ID"]: card for card in cards}
cross_domain = 0
for source, target, weight in space["edges"]:
    assert source in degrees and target in degrees and source != target
    degrees[source] += 1
    degrees[target] += 1
    strengths[source] += weight
    strengths[target] += weight
    cross_domain += cards_by_id[source]["L1_ID"] != cards_by_id[target]["L1_ID"]
assert sum(degrees.values()) == 2 * len(space["edges"])
for point in space["points"]:
    assert degrees[point["id"]] == point["degree"]
    assert math.isclose(strengths[point["id"]], point["strength"], rel_tol=0, abs_tol=2e-6)
assert cross_domain == result["cross_domain"]["edge_count"]
assert math.isclose(cross_domain / len(space["edges"]), result["cross_domain"]["edge_share"])

for metric in [result["degree"], result["strength"]]:
    assert metric["n_tail"] >= result["settings"]["minimum_tail_n"]
    assert metric["alpha"] > 1
    assert 0 <= metric["bootstrap_p"] <= 1
    assert 0 <= metric["vuong_p"] <= 1
assert result["rankings"] == sorted(result["rankings"], key=lambda row: (-row["degree"], -row["strength"], row["id"]))

html = (ROOT / "scale-law-diagnostics.html").read_text()
script = (ROOT / "assets" / "scale-law-diagnostics.js").read_text()
index = (ROOT / "index.html").read_text()
for required in ["Calculation and mathematical specification", "Reproducibility and validation",
                 "Academic significance", "Practical significance", "Limitations", "Prior research"]:
    assert required in html
for doi in ["10.1137/070710111", "10.1038/s41467-019-08746-5", "10.1371/journal.pone.0085777"]:
    assert doi in html
assert 'data-limit="5"' in html and 'data-limit="10"' in html
assert "scale-law-diagnostics.html" in index
assert "neighbor_domains" in script
print("Scale-law diagnostics checks passed: 622 L4 nodes, 55 L3 categories, 3,807 edges, exact graph reconstruction, source hashes, Top-5/10 controls, methods, validation, interpretations, limitations, and references.")
