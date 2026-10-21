#!/usr/bin/env python3
"""Nonvisual integrity tests for the MIT repository ablation."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
try:
    import openpyxl
except ModuleNotFoundError:
    sys.path.append(
        "/Users/deep1003/.cache/codex-runtimes/codex-primary-runtime/dependencies/"
        "python/lib/python3.12/site-packages"
    )
    import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MIT = DATA / "mit_ai_risk_repository"
RAW = MIT / "MIT_AI_Risk_Repository_v4_2025-12-03.xlsx"
PROCESSED = MIT / "mit_ai_risk_records.csv"
EMBEDDINGS = MIT / "mit_bge_m3_embeddings.npz"
RESULT = DATA / "mit_scale_law_ablation.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


result = json.loads(RESULT.read_text())
workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
source_rows = list(workbook["AI Risk Database v4"].iter_rows(min_row=4, values_only=True))
workbook.close()
categories = sum(str(row[7] or "").strip() == "Risk Category" for row in source_rows)
subcategories = sum(str(row[7] or "").strip() == "Risk Sub-Category" for row in source_rows)
assert (categories, subcategories) == (570, 1265)
assert result["node_count"] == categories + subcategories == 1835
assert result["source"]["workbook_sha256"] == digest(RAW)
assert result["source"]["processed_csv_sha256"] == digest(PROCESSED)
assert result["source"]["embedding_sha256"] == digest(EMBEDDINGS)

with PROCESSED.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == 1835
assert len({row["id"] for row in rows}) == 1835
assert [row["id"] for row in rows] == [f"MIT-{index:04d}" for index in range(1, 1836)]

archive = np.load(EMBEDDINGS, allow_pickle=False)
vectors = archive["vectors"]
ids = archive["ids"].tolist()
assert vectors.shape == (1835, 1024)
assert ids == [row["id"] for row in rows]
assert np.isfinite(vectors).all()
assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=2e-5)
assert str(archive["text_sha256"]) == result["source"]["text_sha256"]
assert str(archive["model_revision"]) == result["settings"]["model_revision"]

cosine = vectors @ vectors.T
np.fill_diagonal(cosine, -1)
edges = {}
for index in range(len(rows)):
    for other in np.argsort(-cosine[index], kind="stable")[:8]:
        weight = float(cosine[index, other])
        if weight >= 0.60:
            edge = tuple(sorted((index, int(other))))
            edges[edge] = weight
degree = np.zeros(len(rows), dtype=int)
strength = np.zeros(len(rows), dtype=float)
cross = 0
for (left, right), weight in edges.items():
    degree[left] += 1
    degree[right] += 1
    strength[left] += weight
    strength[right] += weight
    cross += rows[left]["domain"] != rows[right]["domain"]
assert len(edges) == result["edge_count"] == 10847
assert int(degree.sum()) == 2 * len(edges)
assert cross == result["cross_domain"]["edge_count"] == 4572
assert abs(cross / len(edges) - result["cross_domain"]["edge_share"]) < 1e-12
ranking = sorted(range(len(rows)), key=lambda i: (-degree[i], -strength[i], rows[i]["id"]))
assert [rows[i]["id"] for i in ranking] == [item["id"] for item in result["rankings"]]
for index, item in zip(ranking, result["rankings"]):
    assert int(degree[index]) == item["degree"]
    assert abs(float(strength[index]) - item["strength"]) < 1e-6

settings = result["settings"]
assert settings["nearest_neighbours"] == 8
assert settings["cosine_threshold"] == 0.60
assert settings["bootstrap_replicates"] == 1000
assert settings["minimum_tail_n"] == 50
assert settings["seed"] == 20261021
assert result["degree"]["bootstrap_p"] >= 0.10
assert result["strength"]["bootstrap_p"] >= 0.10

html = (ROOT / "mit-scale-law-ablation.html").read_text()
assert "MIT AI Risk Repository scale-law diagnostics" in html
assert "scale-law-diagnostics.html" in html
assert "data/mit_scale_law_ablation.json" in html
assert "https://airisk.mit.edu/risks" in html
index = (ROOT / "index.html").read_text()
assert 'href="mit-scale-law-ablation.html"' in index
print("MIT ablation verification passed: 1,835 records, 10,847 edges, 4,572 cross-domain edges, fixed HEART settings, and linked appendix assets.")
