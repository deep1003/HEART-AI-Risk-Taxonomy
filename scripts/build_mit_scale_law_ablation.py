#!/usr/bin/env python3
"""Build a dataset-substitution ablation with the MIT AI Risk Repository.

The HEART graph settings are held fixed: English risk name and description,
BGE-M3 dense embeddings, cosine similarity, union of each record's eight
nearest neighbours, and a 0.60 edge threshold. The MIT workbook is preserved
as downloaded and is never modified by this script.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
try:
    import openpyxl
except ModuleNotFoundError:
    sys.path.append(
        "/Users/deep1003/.cache/codex-runtimes/codex-primary-runtime/dependencies/"
        "python/lib/python3.12/site-packages"
    )
    import openpyxl

from build_scale_law_diagnostics import (
    BOOTSTRAPS,
    MIN_TAIL,
    SEED,
    bootstrap_p,
    ccdf,
    fit_continuous,
    fit_discrete,
    truncated_lognormal_comparison,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MIT_DIR = DATA / "mit_ai_risk_repository"
RAW = MIT_DIR / "MIT_AI_Risk_Repository_v4_2025-12-03.xlsx"
EMBEDDINGS = MIT_DIR / "mit_bge_m3_embeddings.npz"
PROCESSED = MIT_DIR / "mit_ai_risk_records.csv"
OUTPUT = DATA / "mit_scale_law_ablation.json"
RANKING = DATA / "mit_scale_law_top_risks.csv"
SOURCE_URL = "https://docs.google.com/spreadsheets/d/15LeHcpeuZC9txkvcaMoh3sUhkMvdMMry69xxXL46DT0/export?format=xlsx"
MODEL = "bge-m3:latest"
MODEL_LABEL = "BAAI/bge-m3 (Ollama bge-m3:latest)"
THRESHOLD = 0.60
NEIGHBOURS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalise(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def domain_label(value: object) -> str:
    text = normalise(value)
    if not text or text.startswith("X."):
        return "Uncoded or excluded"
    return text.split(".", 1)[1].strip() if "." in text else text


def refresh_source() -> None:
    MIT_DIR.mkdir(parents=True, exist_ok=True)
    temp = RAW.with_suffix(".download")
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        temp.write_bytes(response.read())
    temp.replace(RAW)


def extract_records() -> list[dict]:
    workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    sheet = workbook["AI Risk Database v4"]
    records = []
    for source_row, row in enumerate(sheet.iter_rows(min_row=4, values_only=True), start=4):
        level = normalise(row[7])
        if level not in {"Risk Category", "Risk Sub-Category"}:
            continue
        risk_category = normalise(row[8])
        risk_subcategory = normalise(row[9])
        name = risk_subcategory or risk_category
        description = normalise(row[10]) or normalise(row[11]) or name
        records.append({
            "id": f"MIT-{len(records) + 1:04d}",
            "source_row": source_row,
            "ev_id": normalise(row[2]),
            "quick_ref": normalise(row[1]),
            "paper_title": normalise(row[0]),
            "category_level": level,
            "risk_category": risk_category,
            "risk_subcategory": risk_subcategory,
            "name": name,
            "description": description,
            "entity": normalise(row[14]),
            "intent": normalise(row[15]),
            "timing": normalise(row[16]),
            "domain_raw": normalise(row[17]),
            "domain": domain_label(row[17]),
            "subdomain": normalise(row[18]),
        })
    workbook.close()
    if not records:
        raise RuntimeError("No MIT risk records were extracted")
    return records


def ollama(path: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:11434/api/{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())


def get_embeddings(records: list[dict], text_hash: str) -> tuple[np.ndarray, str, str]:
    ids = [record["id"] for record in records]
    if EMBEDDINGS.exists():
        cached = np.load(EMBEDDINGS, allow_pickle=False)
        if cached["ids"].tolist() == ids and str(cached["text_sha256"]) == text_hash:
            return cached["vectors"], str(cached["model_revision"]), str(cached["ollama_version"])
    tags = ollama("tags")
    model = next(item for item in tags["models"] if item["name"] == MODEL)
    revision = model["digest"]
    ollama_version = ollama("version")["version"]
    texts = [f'{record["name"]}. {record["description"]}' for record in records]
    vectors = []
    for start in range(0, len(texts), 8):
        response = ollama("embed", {
            "model": MODEL,
            "input": texts[start:start + 8],
            "truncate": False,
            "keep_alive": "10m",
        })
        vectors.extend(response["embeddings"])
        if start % 160 == 0:
            print(f"Embedded {min(start + 8, len(texts))}/{len(texts)}", flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.maximum(norms, 1e-12)
    np.savez_compressed(
        EMBEDDINGS,
        vectors=matrix,
        ids=np.asarray(ids),
        text_sha256=text_hash,
        model_revision=revision,
        ollama_version=ollama_version,
    )
    return matrix, revision, ollama_version


def write_processed(records: list[dict]) -> None:
    fields = list(records[0])
    with PROCESSED.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    if "--refresh" in os.sys.argv or not RAW.exists():
        refresh_source()
    records = extract_records()
    write_processed(records)
    texts = [f'{record["name"]}. {record["description"]}' for record in records]
    text_hash = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    vectors, revision, ollama_version = get_embeddings(records, text_hash)
    if vectors.shape != (len(records), 1024) or not np.isfinite(vectors).all():
        raise RuntimeError(f"Unexpected embedding matrix: {vectors.shape}")

    cosine = vectors @ vectors.T
    np.fill_diagonal(cosine, -1)
    graph = nx.Graph()
    graph.add_nodes_from(range(len(records)))
    for index in range(len(records)):
        for other in np.argsort(-cosine[index], kind="stable")[:NEIGHBOURS]:
            weight = float(cosine[index, other])
            if weight >= THRESHOLD:
                graph.add_edge(index, int(other), weight=weight)

    degrees = np.asarray([graph.degree(i) for i in range(len(records))], dtype=int)
    strengths = np.asarray([
        sum(attrs["weight"] for _, _, attrs in graph.edges(i, data=True))
        for i in range(len(records))
    ], dtype=float)
    degree_fit = fit_discrete(degrees)
    strength_fit = fit_continuous(strengths)
    degree_fit["bootstrap_p"] = bootstrap_p(degrees, degree_fit, True)
    strength_fit["bootstrap_p"] = bootstrap_p(strengths, strength_fit, False)
    degree_fit.update(truncated_lognormal_comparison(degrees, degree_fit, True))
    strength_fit.update(truncated_lognormal_comparison(strengths, strength_fit, False))

    neighbor_domains = []
    rankings = []
    for index, record in enumerate(records):
        counts = Counter(records[other]["domain"] for other in graph.neighbors(index))
        cross = sum(value for key, value in counts.items() if key != record["domain"])
        neighbor_domains.append(counts)
        rankings.append({
            "id": record["id"],
            "ev_id": record["ev_id"],
            "quick_ref": record["quick_ref"],
            "name_en": record["name"],
            "description_en": record["description"],
            "domain": record["domain"],
            "subdomain": record["subdomain"],
            "degree": int(degrees[index]),
            "strength": float(strengths[index]),
            "neighbor_domains": dict(sorted(counts.items())),
            "cross_domain_edges": int(cross),
            "cross_domain_share": float(cross / degrees[index]) if degrees[index] else 0.0,
            "domains_reached": int(len(counts)),
        })
    rankings.sort(key=lambda item: (-item["degree"], -item["strength"], item["id"]))

    cross_edges = sum(records[a]["domain"] != records[b]["domain"] for a, b in graph.edges())
    edge_count = graph.number_of_edges()
    result = {
        "schema_version": "1.0",
        "generated_date": datetime.now(timezone.utc).date().isoformat(),
        "analysis_type": "dataset-substitution ablation",
        "analysis_unit": "MIT AI Risk Repository risk-category and risk-subcategory rows",
        "node_count": len(records),
        "edge_count": edge_count,
        "isolated_nodes": int(sum(value == 0 for value in degrees)),
        "source": {
            "publisher": "MIT AI Risk Initiative",
            "repository_url": "https://airisk.mit.edu/risks",
            "download_url": SOURCE_URL,
            "workbook_file": RAW.name,
            "workbook_sha256": sha256(RAW),
            "workbook_updated": "2025-12-03",
            "retrieved_date": "2026-10-21",
            "sheet": "AI Risk Database v4",
            "included_levels": ["Risk Category", "Risk Sub-Category"],
            "excluded_levels": ["Paper", "Additional evidence"],
            "processed_csv_sha256": sha256(PROCESSED),
            "embedding_sha256": sha256(EMBEDDINGS),
            "text_sha256": text_hash,
            "license": "CC BY 4.0",
        },
        "settings": {
            "embedding_model": MODEL_LABEL,
            "model_revision": revision,
            "ollama_version": ollama_version,
            "embedding_dimensions": 1024,
            "features": "English risk name and description; dense embeddings, no truncation, L2 normalised",
            "nearest_neighbours": NEIGHBOURS,
            "cosine_threshold": THRESHOLD,
            "edge_rule": "Union of each record's eight closest cosine neighbours, cosine >= 0.60; no artificial links",
            "seed": SEED,
            "bootstrap_replicates": BOOTSTRAPS,
            "minimum_tail_n": MIN_TAIL,
        },
        "degree": {"measurement": "incident semantic links", "ccdf": ccdf(degrees), **degree_fit},
        "strength": {"measurement": "sum of incident cosine-similarity weights", "ccdf": ccdf(strengths), **strength_fit},
        "cross_domain": {
            "edge_count": int(cross_edges),
            "edge_share": float(cross_edges / edge_count) if edge_count else 0.0,
            "within_domain_edge_count": int(edge_count - cross_edges),
        },
        "domain_counts": dict(sorted(Counter(record["domain"] for record in records).items())),
        "rankings": rankings,
        "interpretation_rule": (
            "A bootstrap p-value below 0.10 rejects the fitted power-law tail. Otherwise the power law is not rejected, "
            "but it is not established unless the tail is substantial and alternatives are disfavored."
        ),
        "comparability": (
            "The embedding model, text-field pattern, neighbour count, cosine threshold, fitting method, bootstrap count, "
            "minimum tail size, and seed are held fixed relative to HEART. Only the risk inventory is substituted."
        ),
        "limitations": [
            "MIT records are extracted from source frameworks and are not curated to the same granularity as HEART L4 cards.",
            "Repeated or nested concepts from different source frameworks remain separate observations by design.",
            "MIT's seven risk domains differ from HEART's three operating domains, so cross-domain shares are not directly equivalent.",
            "The graph is semantic proximity, not causal propagation, incident co-occurrence, probability, severity, or priority.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with RANKING.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["rank", "MIT_ID", "Ev_ID", "QuickRef", "Risk_name_en", "Domain", "Subdomain", "degree", "strength", "cross_domain_edges", "cross_domain_share"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, item in enumerate(rankings, start=1):
            writer.writerow({
                "rank": rank, "MIT_ID": item["id"], "Ev_ID": item["ev_id"], "QuickRef": item["quick_ref"],
                "Risk_name_en": item["name_en"], "Domain": item["domain"], "Subdomain": item["subdomain"],
                "degree": item["degree"], "strength": f'{item["strength"]:.6f}',
                "cross_domain_edges": item["cross_domain_edges"], "cross_domain_share": f'{item["cross_domain_share"]:.6f}',
            })
    print(json.dumps({
        "records": len(records), "edges": edge_count, "cross_domain": result["cross_domain"],
        "degree": degree_fit, "strength": strength_fit, "top10": rankings[:10],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
