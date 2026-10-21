#!/usr/bin/env python3
"""Normalize three incident sources, map incidents to HEART, and analyse networks.

Analytical grain
----------------
`source_records` retains every source row. `canonical_incidents` uses AIID as
the canonical event whenever OECD AIM supplies an AIID ID; MIT Tracker is an
enrichment of AIID rather than an independent event source. OECD AIM records
without an AIID link remain distinct. Fuzzy duplicate scores are candidates,
never automatic merges.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import time
import urllib.request
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
EVIDENCE = ROOT / "evidence_work" / "incident_analysis"
SITE_DATA = ROOT / "data" / "incidents"
MODEL = "bge-m3:latest"
OLLAMA = "http://127.0.0.1:11434/api/"
SNAPSHOT = "2026-10-21"


def clean(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def json_list(value) -> list:
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            return [clean(value)] if clean(value) else []
    return parsed if isinstance(parsed, list) else [parsed]


def norm_title(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", clean(text).lower()))


def fingerprint(title: str, date: str, entities: str) -> str:
    payload = "|".join((norm_title(title), clean(date)[:10], norm_title(entities)))
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def parse_year(date: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", clean(date))
    return int(match.group()) if match else None


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_sources() -> tuple[list[dict], list[dict], list[dict]]:
    aim_path = Path("/Users/deep1003/data4/aim_pilot/data/2026-08-24/oecd_aim_incidents.jsonl")
    aiid_dir = RAW / "aiid/2026-10-19/mongodump_full_snapshot"
    mit_path = RAW / "mit/2026-10-21/mit_incident_tracker.jsonl"

    mit = [json.loads(line) for line in mit_path.open(encoding="utf-8")]
    mit_by_id = {int(row["incidentId"]): row for row in mit}
    cset = pd.read_csv(aiid_dir / "classifications_CSETv1.csv", low_memory=False)
    cset = cset[cset["Published"] == True].drop_duplicates("Incident ID", keep="last")  # noqa: E712
    cset_by_id = {int(row["Incident ID"]): row for row in cset.to_dict("records")}
    reports = pd.read_csv(aiid_dir / "reports.csv", low_memory=False)
    report_by_id = {int(row["report_number"]): row for row in reports.to_dict("records")}

    aiid = []
    for row in pd.read_csv(aiid_dir / "incidents.csv", low_memory=False).to_dict("records"):
        incident_id = int(row["incident_id"])
        report_ids = [int(value) for value in json_list(row.get("reports"))]
        report_rows = [report_by_id[value] for value in report_ids if value in report_by_id]
        mit_row = mit_by_id.get(incident_id, {})
        cset_row = cset_by_id.get(incident_id, {})
        urls = [clean(value.get("url")) for value in report_rows if clean(value.get("url"))]
        aiid.append(
            {
                "source": "AIID",
                "source_record_id": str(incident_id),
                "record_uid": f"AIID:{incident_id}",
                "canonical_aiid_id": incident_id,
                "incident_title": clean(row.get("title")),
                "risk_name": clean(mit_row.get("subdomain")) or clean(cset_row.get("Harm Domain")),
                "risk_description": clean(row.get("description")),
                "event_date": clean(row.get("date")),
                "event_year": parse_year(row.get("date")),
                "published_date": "",
                "severity_raw": clean(mit_row.get("highestSeverityScore")) or clean(cset_row.get("AI Harm Level")),
                "severity_normalized": mit_row.get("highestSeverityScore") or "",
                "severity_provenance": "MIT Tracker" if mit_row else ("CSETv1" if cset_row else "unavailable"),
                "harm_types": "; ".join(
                    key.replace("SeverityDirect", "")
                    for key, value in mit_row.items()
                    if key.endswith("SeverityDirect") and isinstance(value, (int, float)) and value > 1
                ) or clean(cset_row.get("Harm Domain")),
                "harmed_entities": clean(row.get("Alleged harmed or nearly harmed parties")),
                "countries": clean(cset_row.get("Location Country (two letters)")),
                "industry_sector": clean(cset_row.get("Sector of Deployment")),
                "ai_system": clean(cset_row.get("AI System Description")) or clean(mit_row.get("modelName")),
                "developer": clean(row.get("Alleged developer of AI system")),
                "deployer": clean(row.get("Alleged deployer of AI system")),
                "actual_harm": True,
                "near_miss_possible": True,
                "source_url": f"https://incidentdatabase.ai/cite/{incident_id}",
                "report_urls": json.dumps(urls, ensure_ascii=False),
                "report_count": len(report_ids),
                "source_license": "CC BY-SA 4.0 (database; report contents retain source rights)",
                "source_snapshot": "2026-10-19",
                "source_specific_json": json.dumps(
                    {"report_ids": report_ids, "cset": cset_row}, ensure_ascii=False, default=str
                ),
            }
        )

    aim = []
    for line in aim_path.open(encoding="utf-8"):
        row = json.loads(line)
        properties = row.get("properties") or {}
        if "AI incident" not in (properties.get("harm_levels") or []):
            continue
        aiid_ids = [int(value) for value in row.get("aiid_ids") or []]
        location = row.get("location") or {}
        aim.append(
            {
                "source": "OECD AIM",
                "source_record_id": clean(row.get("id")),
                "record_uid": f"OECD_AIM:{clean(row.get('id'))}",
                "canonical_aiid_id": ";".join(map(str, aiid_ids)),
                "incident_title": clean(row.get("title")),
                "risk_name": "; ".join(properties.get("harm_types") or []),
                "risk_description": clean(row.get("summary")),
                "event_date": clean(row.get("date")),
                "event_year": parse_year(row.get("date")),
                "published_date": clean(row.get("date")),
                "severity_raw": clean(properties.get("most_severe_harm")),
                "severity_normalized": "",
                "severity_provenance": "OECD AIM (field unavailable in snapshot)",
                "harm_types": "; ".join(properties.get("harm_types") or []),
                "harmed_entities": "; ".join(properties.get("harmed_entities") or []),
                "countries": clean(location.get("country_code")) or clean(location.get("country")),
                "industry_sector": "; ".join(properties.get("industries") or []),
                "ai_system": "; ".join(properties.get("ai_tasks") or []),
                "developer": clean(row.get("company")),
                "deployer": clean(row.get("company")),
                "actual_harm": True,
                "near_miss_possible": False,
                "source_url": f"https://oecd.ai/en/incidents/{clean(row.get('id'))}",
                "report_urls": "[]",
                "report_count": row.get("n_articles") or "",
                "source_license": "OECD.AI terms; source articles retain source rights",
                "source_snapshot": "2026-08-24",
                "source_specific_json": json.dumps(
                    {key: value for key, value in row.items() if key not in {"title", "summary"}},
                    ensure_ascii=False,
                ),
            }
        )

    mit_rows = []
    for row in mit:
        incident_id = int(row["incidentId"])
        severity = row.get("highestSeverityScore")
        harm_types = [
            key.replace("SeverityDirect", "")
            for key, value in row.items()
            if key.endswith("SeverityDirect") and isinstance(value, (int, float)) and value > 1
        ]
        mit_rows.append(
            {
                "source": "MIT AI Incident Tracker",
                "source_record_id": str(incident_id),
                "record_uid": f"MIT_TRACKER:{incident_id}",
                "canonical_aiid_id": incident_id,
                "incident_title": clean(row.get("title")),
                "risk_name": clean(row.get("subdomain")),
                "risk_description": clean(row.get("description")) or clean(row.get("summary")),
                "event_date": clean(row.get("date")),
                "event_year": row.get("year") or parse_year(row.get("date")),
                "published_date": clean(row.get("classifiedAt")),
                "severity_raw": clean(severity),
                "severity_normalized": severity or "",
                "severity_provenance": "MIT Tracker / Arcola LLM pipeline",
                "harm_types": "; ".join(harm_types),
                "harmed_entities": clean(row.get("allegedHarmedParties")),
                "countries": clean(row.get("natSecPrimaryTarget")),
                "industry_sector": "",
                "ai_system": clean(row.get("modelName")),
                "developer": clean(row.get("allegedDeveloper")),
                "deployer": clean(row.get("allegedDeployer")),
                "actual_harm": True,
                "near_miss_possible": True,
                "source_url": clean(row.get("url")) or f"https://incidentdatabase.ai/cite/{incident_id}",
                "report_urls": "[]",
                "report_count": row.get("reportCount") or "",
                "source_license": "MIT site: CC BY 4.0; underlying AIID records CC BY-SA 4.0",
                "source_snapshot": "2026-10-21",
                "source_specific_json": json.dumps(row, ensure_ascii=False),
            }
        )
    return aim, aiid, mit_rows


def add_duplicate_fields(rows: list[dict]) -> None:
    for row in rows:
        entities = " ".join((row["developer"], row["deployer"], row["harmed_entities"]))
        row["dedup_title_normalized"] = norm_title(row["incident_title"])
        row["dedup_date_bucket"] = clean(row["event_date"])[:7]
        row["dedup_entity_tokens"] = norm_title(entities)
        row["dedup_fingerprint"] = fingerprint(row["incident_title"], row["event_date"], entities)


def fuzzy_candidates(aim: list[dict], aiid: list[dict]) -> list[dict]:
    """Propose, but never merge, high-similarity AIM↔AIID title candidates."""
    corpus = [row["incident_title"] + " " + row["risk_description"] for row in aiid + aim]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, max_features=80000)
    matrix = vectorizer.fit_transform(corpus)
    aiid_matrix, aim_matrix = matrix[: len(aiid)], matrix[len(aiid) :]
    model = NearestNeighbors(n_neighbors=1, metric="cosine", algorithm="brute").fit(aiid_matrix)
    distances, indices = model.kneighbors(aim_matrix)
    candidates = []
    for row, distance, index in zip(aim, distances[:, 0], indices[:, 0]):
        if row["canonical_aiid_id"]:
            continue
        score = 1 - float(distance)
        target = aiid[int(index)]
        year_delta = None
        if row["event_year"] and target["event_year"]:
            year_delta = abs(int(row["event_year"]) - int(target["event_year"]))
        # Deliberately inclusive review queue: candidates are never auto-merged.
        if score >= 0.55 and (year_delta is None or year_delta <= 1):
            candidates.append(
                {
                    "oecd_aim_record_uid": row["record_uid"],
                    "aiid_record_uid": target["record_uid"],
                    "title_description_tfidf_cosine": round(score, 6),
                    "event_year_delta": year_delta,
                    "disposition": "candidate_only_not_merged",
                }
            )
    return candidates


def build_canonical(aim: list[dict], aiid: list[dict], mit: list[dict]) -> list[dict]:
    mit_by_id = {int(row["canonical_aiid_id"]): row for row in mit}
    aiid_by_id = {int(row["canonical_aiid_id"]): row for row in aiid}
    canonical = []
    for incident_id in sorted(set(aiid_by_id) | set(mit_by_id)):
        base = dict(aiid_by_id.get(incident_id) or mit_by_id[incident_id])
        enrichment = mit_by_id.get(incident_id)
        if enrichment:
            for key in ("risk_name", "severity_raw", "severity_normalized", "severity_provenance", "harm_types", "ai_system"):
                if enrichment.get(key):
                    base[key] = enrichment[key]
        base["canonical_incident_id"] = f"AIID:{incident_id}"
        base["source_coverage"] = "AIID; MIT Tracker" if incident_id in aiid_by_id and incident_id in mit_by_id else ("AIID" if incident_id in aiid_by_id else "MIT Tracker delta")
        canonical.append(base)
    for row in aim:
        if row["canonical_aiid_id"]:
            continue
        base = dict(row)
        base["canonical_incident_id"] = row["record_uid"]
        base["source_coverage"] = "OECD AIM"
        canonical.append(base)
    return canonical


def ollama_embed(texts: list[str], cache: Path) -> np.ndarray:
    model_info = json.load(urllib.request.urlopen(OLLAMA + "tags"))
    model = next(item for item in model_info["models"] if item["name"] == MODEL)
    digest = model["digest"]
    text_hash = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    if cache.exists():
        stored = np.load(cache, allow_pickle=False)
        if str(stored["text_sha256"]) == text_hash and str(stored["model_digest"]) == digest:
            return stored["vectors"]
    vectors = []
    started = time.monotonic()
    for start in range(0, len(texts), 24):
        payload = json.dumps(
            {"model": MODEL, "input": texts[start : start + 24], "truncate": True, "keep_alive": "10m"}
        ).encode()
        request = urllib.request.Request(
            OLLAMA + "embed", data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=600) as response:
            batch = json.load(response)["embeddings"]
        vectors.extend(batch)
        if (start // 24 + 1) % 20 == 0:
            print(f"embedded={len(vectors)}/{len(texts)} elapsed={time.monotonic()-started:.1f}s", flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, vectors=matrix, text_sha256=text_hash, model_digest=digest)
    return matrix


def map_to_heart(canonical: list[dict]) -> list[dict]:
    raw_cards = json.loads((ROOT / "data/heart_l4_risk_cards.json").read_text())
    card_embeddings = np.load(ROOT / "data/semantic_embeddings.npz", allow_pickle=False)
    by_id = {card["L4_ID"]: card for card in raw_cards}
    cards = [by_id[card_id] for card_id in card_embeddings["ids"].tolist()]
    texts = [
        ". ".join(filter(None, (row["incident_title"], row["risk_description"], row["risk_name"], row["harm_types"], row["ai_system"])))[:7000]
        for row in canonical
    ]
    vectors = ollama_embed(texts, EVIDENCE / "canonical_incident_embeddings.npz")
    card_vectors = card_embeddings["vectors"]
    edges = []
    for start in range(0, len(canonical), 512):
        similarities = vectors[start : start + 512] @ card_vectors.T
        top = np.argpartition(-similarities, 5, axis=1)[:, :5]
        for offset, card_indices in enumerate(top):
            incident = canonical[start + offset]
            ordered = sorted(card_indices, key=lambda index: (-similarities[offset, index], cards[index]["L4_ID"]))
            for rank, card_index in enumerate(ordered, 1):
                card = cards[int(card_index)]
                edges.append(
                    {
                        "canonical_incident_id": incident["canonical_incident_id"],
                        "source_coverage": incident["source_coverage"],
                        "event_year": incident["event_year"],
                        "severity_normalized": incident["severity_normalized"],
                        "L4_ID": card["L4_ID"],
                        "L4_Name_en": card["L4_Name_en"],
                        "L3_ID": card["L3_ID"],
                        "L3_Name_en": card["L3_Name_en"],
                        "L2_ID": card["L2_ID"],
                        "L1_ID": card["L1_ID"],
                        "rank": rank,
                        "in_k3": rank <= 3,
                        "in_k5": True,
                        "cosine_similarity": round(float(similarities[offset, card_index]), 6),
                        "mapping_method": "BGE-M3 cosine top-k; no human validation",
                        "taxonomy_snapshot": SNAPSHOT,
                    }
                )
    return edges


def graph_metrics(edges: list[dict], k: int) -> tuple[list[dict], list[dict], dict]:
    selected = [edge for edge in edges if int(edge["rank"]) <= k]
    by_incident: dict[str, list[str]] = defaultdict(list)
    for edge in selected:
        by_incident[edge["canonical_incident_id"]].append(edge["L4_ID"])
    incidence = Counter()
    cooccurrence = Counter()
    for risks in by_incident.values():
        unique = sorted(set(risks))
        incidence.update(unique)
        cooccurrence.update(combinations(unique, 2))
    graph = nx.Graph()
    for risk, count in incidence.items():
        graph.add_node(risk, incident_degree=count)
    for (left, right), count in cooccurrence.items():
        union = incidence[left] + incidence[right] - count
        graph.add_edge(
            left,
            right,
            weight=count,
            jaccard=count / union if union else 0,
            association=count / math.sqrt(incidence[left] * incidence[right]),
        )
    weighted_degree = dict(graph.degree(weight="weight"))
    degree = dict(graph.degree())
    pagerank = nx.pagerank(graph, weight="association") if graph.number_of_nodes() else {}
    betweenness = nx.betweenness_centrality(graph, weight=None) if graph.number_of_nodes() else {}
    communities = nx.community.louvain_communities(graph, weight="association", seed=23) if graph.number_of_edges() else []
    community_of = {node: index + 1 for index, members in enumerate(communities) for node in members}
    cards = {row["L4_ID"]: row for row in json.loads((ROOT / "data/heart_l4_risk_cards.json").read_text())}
    nodes = [
        {
            "L4_ID": node,
            "L4_Name_en": cards[node]["L4_Name_en"],
            "L3_ID": cards[node]["L3_ID"],
            "L1_ID": cards[node]["L1_ID"],
            "incident_degree": incidence[node],
            "network_degree": degree[node],
            "weighted_degree": weighted_degree[node],
            "pagerank": round(pagerank.get(node, 0), 9),
            "betweenness": round(betweenness.get(node, 0), 9),
            "community": community_of.get(node, 0),
        }
        for node in graph.nodes
    ]
    pair_rows = [
        {
            "risk_a": left,
            "risk_b": right,
            "cooccurrence_count": data["weight"],
            "jaccard": round(data["jaccard"], 8),
            "association_strength": round(data["association"], 8),
        }
        for left, right, data in graph.edges(data=True)
    ]
    components = list(nx.connected_components(graph))
    metrics = {
        "k": k,
        "incidents": len(by_incident),
        "risk_nodes": graph.number_of_nodes(),
        "cooccurrence_edges": graph.number_of_edges(),
        "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0,
        "connected_components": len(components),
        "largest_component_nodes": max(map(len, components), default=0),
        "average_clustering_weighted": nx.average_clustering(graph, weight="association") if graph.number_of_nodes() else 0,
        "degree_assortativity": nx.degree_assortativity_coefficient(graph, weight="weight") if graph.number_of_edges() else None,
        "communities": len(communities),
        "modularity": nx.community.modularity(graph, communities, weight="association") if communities else None,
        "degree_distribution": dict(sorted(Counter(degree.values()).items())),
        "incident_degree_distribution": dict(sorted(Counter(incidence.values()).items())),
    }
    return nodes, pair_rows, metrics


def compact_site_data(canonical: list[dict], edges: list[dict], nodes: list[dict], pairs: list[dict], metrics: dict) -> None:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    incident_lookup = {row["canonical_incident_id"]: row for row in canonical}
    edge_lookup: dict[str, list[dict]] = defaultdict(list)
    for edge in edges:
        if edge["in_k3"]:
            edge_lookup[edge["canonical_incident_id"]].append(edge)
    compact = []
    for incident_id, mapped in edge_lookup.items():
        row = incident_lookup[incident_id]
        compact.append(
            {
                "id": incident_id,
                "title": row["incident_title"],
                "year": row["event_year"],
                "source": row["source_coverage"],
                "severity": row["severity_normalized"],
                "url": row["source_url"],
                "risks": [edge["L4_ID"] for edge in sorted(mapped, key=lambda item: item["rank"])],
            }
        )
    (SITE_DATA / "incidents_compact.json").write_text(json.dumps(compact, ensure_ascii=False), encoding="utf-8")
    (SITE_DATA / "network_nodes_k3.json").write_text(json.dumps(nodes, ensure_ascii=False), encoding="utf-8")
    top_pairs = sorted(pairs, key=lambda row: (-row["association_strength"], -row["cooccurrence_count"]))[:1500]
    (SITE_DATA / "network_edges_k3.json").write_text(json.dumps(top_pairs, ensure_ascii=False), encoding="utf-8")
    (SITE_DATA / "network_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-embeddings", action="store_true", help="Only normalize source data")
    args = parser.parse_args()
    PROCESSED.mkdir(exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    aim, aiid, mit = read_sources()
    all_rows = aiid + aim + mit
    add_duplicate_fields(all_rows)
    canonical = build_canonical(aim, aiid, mit)
    candidates = fuzzy_candidates(aim, aiid)
    write_csv(PROCESSED / "source_records.csv", all_rows)
    write_csv(PROCESSED / "canonical_incidents.csv", canonical)
    write_csv(PROCESSED / "duplicate_candidates.csv", candidates)

    quality = {
        "snapshot": SNAPSHOT,
        "source_records": {"OECD AIM actual incidents": len(aim), "AIID incidents": len(aiid), "MIT Tracker derived classifications": len(mit)},
        "canonical_incidents": len(canonical),
        "exact_aim_aiid_links": sum(bool(row["canonical_aiid_id"]) for row in aim),
        "fuzzy_candidates_not_merged": len(candidates),
        "missingness": {
            column: round(sum(not clean(row.get(column)) for row in all_rows) / len(all_rows), 6)
            for column in ("event_date", "risk_name", "risk_description", "severity_normalized", "countries", "industry_sector")
        },
        "grain": "source_records has one row per source record; canonical_incidents collapses exact AIID-linked source overlap only",
    }
    (PROCESSED / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(json.dumps(quality, indent=2))
    if args.skip_embeddings:
        return

    edges = map_to_heart(canonical)
    write_csv(PROCESSED / "incident_heart_edges_k5.csv", edges)
    all_metrics = {}
    k3_nodes = k3_pairs = None
    for k in (3, 5):
        nodes, pairs, metrics = graph_metrics(edges, k)
        write_csv(PROCESSED / f"risk_network_nodes_k{k}.csv", nodes)
        write_csv(PROCESSED / f"risk_cooccurrence_edges_k{k}.csv", pairs)
        all_metrics[f"k{k}"] = metrics
        if k == 3:
            k3_nodes, k3_pairs = nodes, pairs
    (PROCESSED / "network_metrics.json").write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    compact_site_data(canonical, edges, k3_nodes or [], k3_pairs or [], all_metrics)


if __name__ == "__main__":
    main()
