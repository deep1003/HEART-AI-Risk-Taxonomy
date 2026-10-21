#!/usr/bin/env python3
"""Non-visual smoke tests for incident data, mappings, and site assets."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    quality = json.load(open(ROOT / "data/incidents/downloads/data_quality.json"))
    assert quality["canonical_incidents"] == 11119
    compact = json.load(open(ROOT / "data/incidents/incidents_compact.json"))
    assert len(compact) == quality["canonical_incidents"]
    assert len({row["id"] for row in compact}) == len(compact)
    assert all(len(row["risks"]) == 3 for row in compact)

    with gzip.open(ROOT / "data/incidents/downloads/incident_heart_edges_k5.csv.gz", "rt", encoding="utf-8") as handle:
        edges = pd.read_csv(handle)
    assert len(edges) == 5 * len(compact)
    assert set(edges["rank"]) == {1, 2, 3, 4, 5}
    assert edges.groupby("canonical_incident_id").size().eq(5).all()
    assert edges[edges["in_k3"]].groupby("canonical_incident_id").size().eq(3).all()

    metrics = json.load(open(ROOT / "data/incidents/downloads/network_metrics.json"))
    for key in ("k3", "k5"):
        assert metrics[key]["connected_components"] == 1
        assert metrics[key]["incidents"] == len(compact)
    html = (ROOT / "incidents.html").read_text(encoding="utf-8")
    for required in ("OECD AIM", "AI Incident Database", "MIT AI Incident Tracker", "bipartite-network-k3.svg", "risk-cooccurrence-network-k3.svg"):
        assert required in html
    print("incident smoke tests: PASS")


if __name__ == "__main__":
    main()
