#!/usr/bin/env python3
"""Independent incident-mapping validation and network robustness analysis.

The validation embedding excludes source risk labels and harm-type labels. Those
fields are reserved for non-circular external validation.
"""
from __future__ import annotations

import argparse
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
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
MODEL = "bge-m3:latest"
OLLAMA = "http://127.0.0.1:11434/api/"
SEED = 20261021
SNAPSHOT = "2026-10-21"


def norm(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def truthy(value) -> bool:
    return norm(value).lower() in {"yes", "true", "1"}


def embed(texts: list[str], cache: Path) -> np.ndarray:
    tags = json.load(urllib.request.urlopen(OLLAMA + "tags"))
    model = next(item for item in tags["models"] if item["name"] == MODEL)
    digest = model["digest"]
    text_hash = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    if cache.exists():
        stored = np.load(cache, allow_pickle=False)
        if str(stored["text_sha256"]) == text_hash and str(stored["model_digest"]) == digest:
            return stored["vectors"]
    vectors: list[list[float]] = []
    started = time.monotonic()
    for start in range(0, len(texts), 24):
        payload = json.dumps({"model": MODEL, "input": texts[start:start + 24], "truncate": True,
                              "keep_alive": "10m"}).encode()
        req = urllib.request.Request(OLLAMA + "embed", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as response:
            vectors.extend(json.load(response)["embeddings"])
        if (start // 24 + 1) % 40 == 0:
            print(f"embedded={len(vectors)}/{len(texts)} elapsed={time.monotonic()-started:.1f}s", flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, vectors=matrix, text_sha256=text_hash, model_digest=digest)
    return matrix


def canonical_text(source: pd.DataFrame) -> pd.DataFrame:
    source = source.copy()
    linked_aim = source.source.eq("OECD AIM") & source.canonical_aiid_id.fillna("").astype(str).str.len().gt(0)
    source = source[~linked_aim].copy()
    source["canonical_id"] = source.apply(
        lambda r: f"AIID:{int(float(r.canonical_aiid_id))}" if pd.notna(r.canonical_aiid_id)
        else str(r.record_uid), axis=1)
    rows = []
    for incident_id, group in source.groupby("canonical_id", sort=True):
        def longest(column: str) -> str:
            values = [norm(x) for x in group[column].tolist() if norm(x)]
            return max(values, key=len, default="")
        rows.append({
            "canonical_incident_id": incident_id,
            "incident_title": longest("incident_title"),
            "incident_description": longest("risk_description"),
            "ai_system": longest("ai_system"),
            "event_year": pd.to_numeric(group["event_year"], errors="coerce").dropna().min(),
            "source_coverage": "; ".join(sorted(group["source"].dropna().unique())),
            "source_url": longest("source_url"),
        })
    out = pd.DataFrame(rows)
    out["validation_text"] = out.apply(
        lambda r: ". ".join(x for x in [r.incident_title, r.incident_description, r.ai_system] if x)[:7000], axis=1)
    return out


def map_cards(canonical: pd.DataFrame, cache: Path) -> pd.DataFrame:
    cards = pd.read_json(ROOT / "data/heart_l4_risk_cards.json").sort_values("L4_ID").reset_index(drop=True)
    stored = np.load(ROOT / "data/semantic_embeddings.npz", allow_pickle=False)
    order = {card_id: i for i, card_id in enumerate(stored["ids"].tolist())}
    cards["vector_index"] = cards.L4_ID.map(order)
    assert cards.vector_index.notna().all()
    card_vectors = stored["vectors"][cards.vector_index.astype(int)]
    vectors = embed(canonical.validation_text.tolist(), cache)
    rows = []
    for start in range(0, len(canonical), 512):
        sims = vectors[start:start + 512] @ card_vectors.T
        top = np.argpartition(-sims, 5, axis=1)[:, :5]
        for offset, indexes in enumerate(top):
            incident = canonical.iloc[start + offset]
            ordered = sorted(indexes, key=lambda i: (-sims[offset, i], cards.iloc[i].L4_ID))
            for rank, i in enumerate(ordered, 1):
                card = cards.iloc[int(i)]
                rows.append({"canonical_incident_id": incident.canonical_incident_id,
                             "L4_ID": card.L4_ID, "L4_Name_en": card.L4_Name_en,
                             "L3_ID": card.L3_ID, "L3_Name_en": card.L3_Name_en,
                             "L2_ID": card.L2_ID, "L1_ID": card.L1_ID, "rank": rank,
                             "cosine_similarity": round(float(sims[offset, i]), 6)})
    return pd.DataFrame(rows)


PHYSICAL_GOALS = {
    "autonomous driving", "robotic manipulation", "robotics", "drone navigation",
    "smart devices", "medical diagnosis", "biometric identification", "gunshot detection",
}
PHYSICAL_TEXT = re.compile(
    r"\b(?:autonomous|self[- ]driving|driverless|robot(?:ic)?|drone|vehicle|shuttle|bus|car|truck|"
    r"aircraft|surgical|medical device|warehouse|fulfilment|fulfillment|factory|machinery|physical control|"
    r"smart device|thermostat|smoke detector)\b", re.I)
FALSE_POSITIVE_TEXT = re.compile(
    r"\b(?:deepfake|image generation|voice generation|tim cook|roger cook|cookware|cooking advice|"
    r"content recommendation|facial recognition)\b", re.I)


def load_external(mit_path: Path, cset_dir: Path, source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mit_rows = [json.loads(line) for line in mit_path.read_text().splitlines() if line.strip()]
    mit = pd.DataFrame(mit_rows)
    mit["canonical_incident_id"] = "AIID:" + mit.incidentId.astype(int).astype(str)
    mit["mit_label_available"] = True
    mit["external_agentic"] = mit.behaviourType.str.lower().isin(["agent", "multi-agent"])
    goals = (mit.aiGoalPrimary.fillna("") + "; " + mit.aiGoalSecondary.fillna("")).str.lower()
    mit["external_physical"] = goals.apply(lambda x: any(goal in x for goal in PHYSICAL_GOALS))
    mit["external_mit_label"] = mit.domain.fillna("") + " | " + mit.subdomain.fillna("")

    csets = []
    for name in ["classifications_CSETv1.csv", "classifications_CSETv0.csv"]:
        path = next(cset_dir.rglob(name), None)
        if path is None:
            continue
        df = pd.read_csv(path, low_memory=False)
        df = df[df["Published"].astype(str).str.lower().eq("true")].copy()
        df["canonical_incident_id"] = "AIID:" + pd.to_numeric(df["Incident ID"], errors="coerce").astype("Int64").astype(str)
        if name.endswith("v1.csv"):
            ps = df.get("Physical System Type", pd.Series("", index=df.index)).fillna("").astype(str)
            desc = df.get("AI System Description", pd.Series("", index=df.index)).fillna("").astype(str)
            df["external_physical"] = (df.get("Physical Objects", "").astype(str).str.lower().eq("yes") |
                                       ps.str.len().gt(1) | desc.str.contains(PHYSICAL_TEXT))
            df["external_cset_label"] = (df.get("AI Harm Level", "").fillna("").astype(str) + " | " +
                                          df.get("Physical System Type", "").fillna("").astype(str))
        else:
            ps = df.get("Physical System", pd.Series("", index=df.index)).fillna("").astype(str)
            desc = df.get("AI System Description", pd.Series("", index=df.index)).fillna("").astype(str)
            harm = df.get("Harm Type", pd.Series("", index=df.index)).fillna("").astype(str)
            df["external_physical"] = ps.str.len().gt(1) | desc.str.contains(PHYSICAL_TEXT) | harm.str.contains("physical", case=False)
            df["external_cset_label"] = harm + " | " + ps
        csets.append(df[["canonical_incident_id", "external_physical", "external_cset_label"]])
    cset = pd.concat(csets, ignore_index=True) if csets else pd.DataFrame(columns=["canonical_incident_id", "external_physical", "external_cset_label"])
    cset = cset.groupby("canonical_incident_id", as_index=False).agg(
        external_physical=("external_physical", "max"),
        external_cset_label=("external_cset_label", lambda x: " || ".join(sorted(set(filter(None, map(norm, x)))))))
    cset["cset_label_available"] = True

    aim = source[source.source.eq("OECD AIM")].copy()
    expanded = []
    for _, row in aim.iterrows():
        ids = [item for item in norm(row.canonical_aiid_id).split(";") if item]
        canonical_ids = [f"AIID:{int(float(item))}" for item in ids] if ids else [str(row.record_uid)]
        for incident_id in canonical_ids:
            copy = row.copy(); copy["canonical_incident_id"] = incident_id; expanded.append(copy)
    aim = pd.DataFrame(expanded)
    labels = (aim.harm_types.fillna("") + "; " + aim.risk_name.fillna(""))
    aim["external_physical"] = labels.str.contains(r"physical|injur|death|safety|vehicle|robot|medical", case=False)
    aim = aim.groupby("canonical_incident_id", as_index=False).agg(
        external_physical=("external_physical", "max"),
        external_aim_label=("harm_types", lambda x: " || ".join(sorted(set(filter(None, map(norm, x)))))))
    aim["aim_label_available"] = True
    return mit, pd.merge(cset, aim, on="canonical_incident_id", how="outer", suffixes=("_cset", "_aim"))


def define_embodied(canonical: pd.DataFrame, mit: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    out = canonical.copy()
    mitcols = mit[["canonical_incident_id", "mit_label_available", "external_physical", "external_agentic", "external_mit_label",
                   "intent", "behaviourType", "aiGoalPrimary", "aiGoalSecondary"]].rename(columns={"external_physical": "mit_physical"})
    out = out.merge(mitcols, on="canonical_incident_id", how="left").merge(labels, on="canonical_incident_id", how="left")
    for col in ["mit_physical", "external_agentic", "external_physical_cset", "external_physical_aim"]:
        if col not in out: out[col] = False
        out[col] = out[col].fillna(False).astype(bool)
    for col in ["mit_label_available", "cset_label_available", "aim_label_available"]:
        if col not in out: out[col] = False
        out[col] = out[col].fillna(False).astype(bool)
    text = out.incident_title.fillna("") + ". " + out.incident_description.fillna("") + ". " + out.ai_system.fillna("")
    out["text_physical_positive"] = text.str.contains(PHYSICAL_TEXT)
    out["text_false_positive"] = text.str.contains(FALSE_POSITIVE_TEXT)
    out["embodied_strong_external"] = out.mit_physical | out.external_physical_cset
    out["embodied_rule"] = out.embodied_strong_external | (out.text_physical_positive & ~out.text_false_positive)
    out["embodied_rule_basis"] = out.apply(lambda r: "; ".join([
        name for name, flag in [("MIT physical goal", r.mit_physical), ("CSET physical-system label", r.external_physical_cset),
                                ("physical-system text", r.text_physical_positive and not r.text_false_positive)] if flag]), axis=1)
    return out


def domain_sets(edges: pd.DataFrame, k: int) -> pd.DataFrame:
    rows = []
    for incident, group in edges[edges["rank"].le(k)].groupby("canonical_incident_id"):
        domains = sorted(group.L1_ID.unique())
        rows.append({"canonical_incident_id": incident, f"domains_k{k}": ";".join(domains),
                     f"domain_count_k{k}": len(domains), f"cross_domain_k{k}": len(domains) > 1,
                     f"has_general_k{k}": "L1_G" in domains, f"has_agentic_k{k}": "L1_A" in domains,
                     f"has_physical_k{k}": "L1_P" in domains})
    return pd.DataFrame(rows)


def binary_metrics(y: pd.Series, pred: pd.Series) -> dict:
    y, pred = y.astype(bool).to_numpy(), pred.astype(bool).to_numpy()
    tp, tn = int(np.sum(y & pred)), int(np.sum(~y & ~pred))
    fp, fn = int(np.sum(~y & pred)), int(np.sum(y & ~pred))
    n = len(y)
    acc = (tp + tn) / n if n else math.nan
    precision = tp / (tp + fp) if tp + fp else math.nan
    recall = tp / (tp + fn) if tp + fn else math.nan
    den = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    mcc = ((tp*tn)-(fp*fn))/den if den else math.nan
    return {"n": n, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "accuracy": acc,
            "precision": precision, "recall": recall, "mcc": mcc}


def null_test(edges: pd.DataFrame, embodied_ids: set[str], permutations: int) -> dict:
    e = edges[edges["rank"].le(3)].copy().reset_index(drop=True)
    e["sim_bin"] = pd.qcut(e.cosine_similarity, 10, labels=False, duplicates="drop")
    incident_codes, incidents = pd.factorize(e.canonical_incident_id)
    embodied_mask = np.array([item in embodied_ids for item in incidents])
    observed_domains = e.L1_ID.to_numpy().copy()
    rng = np.random.default_rng(SEED)
    strata = [idx.to_numpy() for _, idx in e.groupby(["rank", "sim_bin"]).groups.items()]

    def rate(domains: np.ndarray) -> float:
        masks = {d: np.zeros(len(incidents), dtype=bool) for d in ["L1_G", "L1_A", "L1_P"]}
        for d, mask in masks.items():
            np.logical_or.at(mask, incident_codes, domains == d)
        counts = sum(mask.astype(np.int8) for mask in masks.values())
        return float(np.mean(counts[embodied_mask] > 1))

    observed = rate(observed_domains)
    null = np.empty(permutations)
    for i in range(permutations):
        shuffled = observed_domains.copy()
        for indexes in strata:
            shuffled[indexes] = rng.permutation(shuffled[indexes])
        null[i] = rate(shuffled)
    return {"permutations": permutations, "embodied_n": int(embodied_mask.sum()), "observed_cross_domain_rate": observed,
            "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)),
            "null_p95": float(np.quantile(null, .95)),
            "one_sided_p": float((1 + np.sum(null >= observed)) / (permutations + 1)),
            "z_score": float((observed-null.mean())/null.std(ddof=1)), "seed": SEED,
            "null_rule": "Within rank × cosine-decile strata, permute card/domain assignments across incident edges."}


def projected_graph(edges: pd.DataFrame, k: int) -> nx.Graph:
    graph = nx.Graph()
    for _, group in edges[edges["rank"].le(k)].groupby("canonical_incident_id"):
        cards = sorted(set(group.L4_ID))
        graph.add_nodes_from(cards)
        for a, b in combinations(cards, 2):
            graph.add_edge(a, b, weight=graph.get_edge_data(a, b, {}).get("weight", 0) + 1)
    return graph


def bridge_tables(edges: pd.DataFrame, cards: pd.DataFrame) -> pd.DataFrame:
    semantic = json.loads((ROOT / "data/semantic_space.json").read_text())
    semantic_full = nx.Graph()
    semantic_full.add_weighted_edges_from(semantic["edges"])
    rows = []
    card_index = cards.set_index("L4_ID")
    for k in [3, 5]:
        incident = projected_graph(edges, k)
        active = set(incident)
        sem = semantic_full.subgraph(active).copy()
        for kind, graph in [("semantic", sem), ("incident", incident)]:
            bet = nx.betweenness_centrality(graph, weight=None)
            for rank, (node, value) in enumerate(sorted(bet.items(), key=lambda x: (-x[1], x[0]))[:20], 1):
                domains = Counter(card_index.loc[n, "L1_ID"] for n in graph.neighbors(node))
                cross = sum(v for d, v in domains.items() if d != card_index.loc[node, "L1_ID"])
                rows.append({"network": kind, "k": k, "rank": rank, "L4_ID": node,
                             "L4_Name_en": card_index.loc[node, "L4_Name_en"], "L1_ID": card_index.loc[node, "L1_ID"],
                             "betweenness": value, "degree": graph.degree(node), "cross_domain_degree": cross,
                             "cross_domain_share": cross / graph.degree(node) if graph.degree(node) else 0})
    return pd.DataFrame(rows)


def hubness(edges: pd.DataFrame, cards: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stored = np.load(ROOT / "data/semantic_embeddings.npz", allow_pickle=False)
    ids = stored["ids"].tolist(); vec = stored["vectors"]
    centroid = vec.mean(axis=0); centroid /= np.linalg.norm(centroid)
    generic = vec @ centroid
    card = cards.set_index("L4_ID").loc[ids].reset_index()
    card["centroid_similarity"] = generic
    counts = edges[edges["rank"].le(3)].L4_ID.value_counts()
    card["incident_degree_k3"] = card.L4_ID.map(counts).fillna(0).astype(int)
    y = np.log1p(card.incident_degree_k3)
    dummies = pd.get_dummies(card.L1_ID, prefix="L1", drop_first=True, dtype=float)
    X = pd.concat([card[["centroid_similarity"]], dummies], axis=1).astype(float)
    X = sm.add_constant(X)
    fit = sm.OLS(y, X).fit()
    card["expected_log_degree"] = fit.predict(X)
    card["hubness_residual"] = y - card.expected_log_degree
    card["residual_rank"] = card.hubness_residual.rank(method="min", ascending=False).astype(int)
    card["raw_degree_rank"] = card.incident_degree_k3.rank(method="min", ascending=False).astype(int)
    card = card.sort_values(["residual_rank", "L4_ID"])
    stats = {"model": "log1p(incident_degree_k3) ~ centroid_similarity + L1 fixed effects",
             "n_cards": len(card), "r_squared": fit.rsquared, "centroid_coefficient": fit.params["centroid_similarity"],
             "centroid_p_value": fit.pvalues["centroid_similarity"]}
    return card, stats


BENIGN_PATTERNS = {
    "benign request misinterpreted": re.compile(r"asked|request|misinterpret|mistakenly|directions|recommended", re.I),
    "task overreach or unauthorized action": re.compile(r"unauthori[sz]ed|without user consent|instead deleted|production database|bypassed", re.I),
    "unsafe assistance to ordinary request": re.compile(r"advice|instructions|suggested|helped|answer|query|assistant", re.I),
}


def benign_cases(mit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in mit.iterrows():
        if norm(r.intent).lower() != "unintentional" or norm(r.behaviourType).lower() not in {"assistant", "agent", "autonomous"}:
            continue
        text = " ".join([norm(r.title), norm(r.summary), norm(r.description)])
        matched = [name for name, pattern in BENIGN_PATTERNS.items() if pattern.search(text)]
        if not matched:
            continue
        score = 0
        score += 2 * bool(re.search(r"asked|requested|directions|task|organize|price comparison", text, re.I))
        score += 2 * bool(re.search(r"danger|harm|deleted|unauthori[sz]ed|injur|suicid|lake|private conversation", text, re.I))
        score += bool(norm(r.behaviourType).lower() == "agent")
        rows.append({"canonical_incident_id": r.canonical_incident_id, "incident_title": r.title,
                     "case_type": "; ".join(matched), "screening_score": score,
                     "intent": r.intent, "behaviour_type": r.behaviourType,
                     "ai_goal": f"{norm(r.aiGoalPrimary)}; {norm(r.aiGoalSecondary)}".strip("; "),
                     "evidence_excerpt": norm(r.description), "source_url": r.url,
                     "verification_status": "Database-reported case; original linked reports not independently adjudicated"})
    return pd.DataFrame(rows).sort_values(["screening_score", "canonical_incident_id"], ascending=[False, True])


def validation_sample(incidents: pd.DataFrame, edges: pd.DataFrame, n: int = 150) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    top = edges[edges["rank"].le(3)].pivot(index="canonical_incident_id", columns="rank", values=["L4_ID", "L4_Name_en", "cosine_similarity"])
    top.columns = [f"{a}_{b}" for a, b in top.columns]
    frame = incidents.merge(top.reset_index(), on="canonical_incident_id", how="left")
    frame["source_stratum"] = np.where(frame.source_coverage.str.contains("AIID"), "AIID-linked", "AIM-only")
    frame["cross_stratum"] = np.where(frame.cross_domain_k3, "cross-domain", "single-domain")
    frame["embodied_stratum"] = np.where(frame.embodied_rule, "embodied-candidate", "other")
    selected = []
    embodied = frame[frame.embodied_rule].sample(n=min(50, frame.embodied_rule.sum()), random_state=SEED)
    selected.append(embodied)
    remaining = frame.drop(embodied.index)
    quotas = {("AIID-linked", "cross-domain"): 25, ("AIID-linked", "single-domain"): 25,
              ("AIM-only", "cross-domain"): 25, ("AIM-only", "single-domain"): 25}
    for (source, cross), quota in quotas.items():
        pool = remaining[(remaining.source_stratum == source) & (remaining.cross_stratum == cross)]
        take = min(quota, len(pool))
        choice = pool.sample(n=take, random_state=int(rng.integers(0, 2**31-1)))
        selected.append(choice); remaining = remaining.drop(choice.index)
    sample = pd.concat(selected).drop_duplicates("canonical_incident_id")
    if len(sample) < n:
        sample = pd.concat([sample, remaining.sample(n=n-len(sample), random_state=SEED)]).drop_duplicates("canonical_incident_id")
    sample = sample.head(n).copy()
    sample.insert(0, "sample_id", [f"HV-{i:03d}" for i in range(1, len(sample)+1)])
    for col in ["reviewer_id", "reviewed_at", "embodied_confirmed", "top1_relevant", "top2_relevant", "top3_relevant",
                "missing_better_card_id", "adjudication_notes"]:
        sample[col] = ""
    return sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-records", type=Path, required=True)
    parser.add_argument("--mit", type=Path, required=True)
    parser.add_argument("--cset-dir", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=ROOT / "work/incident_validation")
    parser.add_argument("--out", type=Path, default=ROOT / "data/incidents/validation")
    parser.add_argument("--permutations", type=int, default=2000)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True); args.out.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(args.source_records, low_memory=False)
    canonical = canonical_text(source)
    edges = map_cards(canonical, args.work / "noncircular_incident_embeddings.npz")
    mit, external = load_external(args.mit, args.cset_dir, source)
    incidents = define_embodied(canonical, mit, external)
    incidents = incidents.merge(domain_sets(edges, 3), on="canonical_incident_id").merge(domain_sets(edges, 5), on="canonical_incident_id")

    validations = []
    checks = [
        ("MIT agent/multi-agent behaviour → Agentic HEART card", incidents.mit_label_available, incidents.external_agentic, incidents.has_agentic_k3),
        ("MIT physical AI goal → Physical HEART card", incidents.mit_label_available, incidents.mit_physical, incidents.has_physical_k3),
        ("CSET physical-system label → Physical HEART card", incidents.cset_label_available, incidents.external_physical_cset, incidents.has_physical_k3),
        ("AIM physical-harm label → Physical HEART card", incidents.aim_label_available, incidents.external_physical_aim, incidents.has_physical_k3),
    ]
    for name, available, signal, predicted in checks:
        mask = available.astype(bool)
        row = {"validation_test": name, **binary_metrics(signal[mask], predicted[mask])}
        validations.append(row)
    validation_df = pd.DataFrame(validations)

    null = null_test(edges, set(incidents.loc[incidents.embodied_rule, "canonical_incident_id"]), args.permutations)
    cards = pd.read_json(ROOT / "data/heart_l4_risk_cards.json")
    bridges = bridge_tables(edges, cards)
    residuals, hub_stats = hubness(edges, cards)
    benign = benign_cases(mit)
    sample = validation_sample(incidents, edges, 150)
    strong = incidents[incidents.embodied_strong_external].sample(
        n=min(50, int(incidents.embodied_strong_external.sum())), random_state=SEED)
    text_only_pool = incidents[incidents.embodied_rule & ~incidents.embodied_strong_external]
    text_only = text_only_pool.sample(n=min(50, len(text_only_pool)), random_state=SEED)
    embodied_audit = pd.concat([strong, text_only]).drop_duplicates("canonical_incident_id").head(100).copy()
    embodied_audit.insert(0, "audit_id", [f"EMB-{i:03d}" for i in range(1, len(embodied_audit)+1)])
    for col in ["human_embodied_confirmed", "false_positive_reason", "reviewer_id", "reviewed_at", "review_notes"]:
        embodied_audit[col] = ""

    edges.to_csv(args.out / "noncircular_incident_heart_edges_k5.csv.gz", index=False, compression="gzip")
    incidents.to_csv(args.out / "embodied_subset_audit.csv.gz", index=False, compression="gzip")
    validation_df.to_csv(args.out / "external_label_validation.csv", index=False)
    bridges.to_csv(args.out / "bridge_analysis_k3_k5.csv", index=False)
    residuals.to_csv(args.out / "hubness_residuals.csv", index=False)
    benign.head(100).to_csv(args.out / "benign_intent_cases.csv", index=False)
    sample.to_csv(args.out / "human_validation_sample_150.csv", index=False)
    embodied_audit.to_csv(args.out / "embodied_rule_audit_sample_100.csv", index=False)
    summary = {
        "snapshot": SNAPSHOT, "canonical_incidents": len(canonical), "human_validation": {
            "sample_n": len(sample), "status": "PENDING HUMAN ADJUDICATION",
            "embodied_candidates_in_sample": int(sample.embodied_rule.sum()),
            "embodied_rule_audit_n": len(embodied_audit),
            "instruction": "A human reviewer must complete the blank adjudication columns; no AI judgement is reported as human validation."},
        "noncircular_mapping": {"text_fields": ["incident_title", "incident_description", "ai_system"],
                                "excluded_validation_fields": ["risk_name", "harm_types", "MIT risk domain", "CSET labels"],
                                "external_validation": validation_df.to_dict("records")},
        "embodied_subset": {"n": int(incidents.embodied_rule.sum()),
                             "strong_external_n": int(incidents.embodied_strong_external.sum()),
                             "rule": "Strong MIT/CSET physical-system label OR contextual physical-system text, excluding named-person/deepfake/content false positives."},
        "incident_null": null, "hubness_control": hub_stats,
        "benign_intent": {"screened_candidates": len(benign), "published_top_n": min(100, len(benign)),
                          "microwave_literal_match": 0,
                          "finding": "No literal microwave incident. Closest verified database-reported analogues include Alexa's penny challenge, harmful Google AI advice, Waze navigation into a lake, and task-overreach by Operator/Claude/Cursor."},
        "limitations": ["Human adjudication is not yet complete.", "External labels are incomplete and source-specific.",
                        "Embodied rules remain a candidate definition until human review.",
                        "Database-reported benign-intent cases were not independently adjudicated against every original news report."],
    }
    (args.out / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({"incidents": len(canonical), "edges": len(edges), "embodied": summary["embodied_subset"],
                      "null": null, "human_sample": summary["human_validation"], "benign": summary["benign_intent"]}, indent=2))


if __name__ == "__main__":
    main()
