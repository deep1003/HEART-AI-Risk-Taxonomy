#!/usr/bin/env python3
"""Build reproducible L4 semantic-network scale-law diagnostics.

The published graph is fixed by data/semantic_space.json. This script does not
change taxonomy assignments or graph edges. It fits candidate power-law tails,
performs deterministic semi-parametric bootstrap checks, compares a truncated
lognormal alternative, and writes machine-readable results for the website.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 20261021
BOOTSTRAPS = 1000
MIN_TAIL = 50


def discrete_alpha(values: np.ndarray, xmin: int) -> float:
    tail = values[values >= xmin]
    return 1.0 + len(tail) / np.log(tail / (xmin - 0.5)).sum()


def discrete_ks(values: np.ndarray, xmin: int, alpha: float) -> float:
    tail = np.sort(values[values >= xmin])
    empirical = np.arange(1, len(tail) + 1) / len(tail)
    model = 1.0 - special.zeta(alpha, tail + 1) / special.zeta(alpha, xmin)
    return float(np.max(np.abs(empirical - model)))


def fit_discrete(values: np.ndarray) -> dict:
    candidates = [int(x) for x in np.unique(values) if np.sum(values >= x) >= MIN_TAIL]
    fits = []
    for xmin in candidates:
        alpha = discrete_alpha(values, xmin)
        fits.append((discrete_ks(values, xmin, alpha), xmin, alpha, int(np.sum(values >= xmin))))
    ks, xmin, alpha, n_tail = min(fits)
    return {"xmin": xmin, "alpha": alpha, "ks": ks, "n_tail": n_tail}


def continuous_alpha(values: np.ndarray, xmin: float) -> float:
    tail = values[values >= xmin]
    return 1.0 + len(tail) / np.log(tail / xmin).sum()


def continuous_ks(values: np.ndarray, xmin: float, alpha: float) -> float:
    tail = np.sort(values[values >= xmin])
    empirical = np.arange(1, len(tail) + 1) / len(tail)
    model = 1.0 - (tail / xmin) ** (1.0 - alpha)
    return float(np.max(np.abs(empirical - model)))


def fit_continuous(values: np.ndarray) -> dict:
    candidates = [float(x) for x in np.unique(values) if np.sum(values >= x) >= MIN_TAIL]
    fits = []
    for xmin in candidates:
        alpha = continuous_alpha(values, xmin)
        fits.append((continuous_ks(values, xmin, alpha), xmin, alpha, int(np.sum(values >= xmin))))
    ks, xmin, alpha, n_tail = min(fits)
    return {"xmin": xmin, "alpha": alpha, "ks": ks, "n_tail": n_tail}


def discrete_sample(alpha: float, xmin: int, size: int, rng: np.random.Generator) -> np.ndarray:
    upper = max(1000, xmin * 40)
    support = np.arange(xmin, upper + 1)
    weights = support.astype(float) ** (-alpha)
    weights /= weights.sum()
    return rng.choice(support, size=size, p=weights)


def bootstrap_p(values: np.ndarray, fit: dict, discrete: bool) -> float:
    rng = np.random.default_rng(SEED + (0 if discrete else 1))
    below = values[values < fit["xmin"]]
    n_tail = fit["n_tail"]
    exceed = 0
    completed = 0
    fitter = fit_discrete if discrete else fit_continuous
    for _ in range(BOOTSTRAPS):
        lower = rng.choice(below, size=len(below), replace=True) if len(below) else np.array([])
        if discrete:
            tail = discrete_sample(fit["alpha"], int(fit["xmin"]), n_tail, rng)
        else:
            tail = fit["xmin"] * (1.0 - rng.random(n_tail)) ** (-1.0 / (fit["alpha"] - 1.0))
        sample = np.concatenate([lower, tail])
        try:
            synthetic_fit = fitter(sample)
        except (ValueError, ZeroDivisionError, FloatingPointError):
            continue
        exceed += synthetic_fit["ks"] >= fit["ks"]
        completed += 1
    return exceed / completed


def truncated_lognormal_comparison(values: np.ndarray, fit: dict, discrete: bool) -> dict:
    xmin = fit["xmin"]
    tail = values[values >= xmin].astype(float)
    log_tail = np.log(tail)

    if discrete:
        max_support = max(10000, int(tail.max() * 200))
        support = np.arange(int(xmin), max_support + 1, dtype=float)

        def lognormal_ll(params: np.ndarray) -> float:
            mu, log_sigma = params
            sigma = math.exp(log_sigma)
            logw = -np.log(support) - ((np.log(support) - mu) ** 2) / (2 * sigma**2)
            logz = special.logsumexp(logw)
            return float(np.sum(-log_tail - ((log_tail - mu) ** 2) / (2 * sigma**2) - logz))

        result = optimize.minimize(lambda p: -lognormal_ll(p), [log_tail.mean(), math.log(max(log_tail.std(), 0.1))])
        mu, log_sigma = result.x
        sigma = math.exp(log_sigma)
        logw = -np.log(support) - ((np.log(support) - mu) ** 2) / (2 * sigma**2)
        logz = special.logsumexp(logw)
        ll_ln = -log_tail - ((log_tail - mu) ** 2) / (2 * sigma**2) - logz
        ll_pl = -fit["alpha"] * log_tail - math.log(special.zeta(fit["alpha"], int(xmin)))
    else:
        def lognormal_ll(params: np.ndarray) -> float:
            mu, log_sigma = params
            sigma = math.exp(log_sigma)
            survival = stats.norm.sf((math.log(xmin) - mu) / sigma)
            if survival <= 0:
                return -np.inf
            return float(np.sum(-log_tail - math.log(sigma) - 0.5 * math.log(2 * math.pi)
                                - ((log_tail - mu) ** 2) / (2 * sigma**2) - math.log(survival)))

        result = optimize.minimize(lambda p: -lognormal_ll(p), [log_tail.mean(), math.log(max(log_tail.std(), 0.1))])
        mu, log_sigma = result.x
        sigma = math.exp(log_sigma)
        survival = stats.norm.sf((math.log(xmin) - mu) / sigma)
        ll_ln = -log_tail - math.log(sigma) - 0.5 * math.log(2 * math.pi) \
            - ((log_tail - mu) ** 2) / (2 * sigma**2) - math.log(survival)
        ll_pl = math.log(fit["alpha"] - 1.0) - math.log(xmin) - fit["alpha"] * np.log(tail / xmin)

    differences = ll_pl - ll_ln
    ratio = float(differences.sum())
    standard_error = float(differences.std(ddof=1) / math.sqrt(len(differences))) if len(differences) > 1 else math.inf
    z_score = float(differences.mean() / standard_error) if standard_error > 0 else 0.0
    p_value = float(2 * stats.norm.sf(abs(z_score)))
    preferred = "power law" if ratio > 0 else "lognormal"
    return {"log_likelihood_ratio_powerlaw_vs_lognormal": ratio, "vuong_z": z_score,
            "vuong_p": p_value, "preferred_by_sign": preferred, "lognormal_mu": float(mu),
            "lognormal_sigma": float(sigma)}


def ccdf(values: np.ndarray) -> list[dict]:
    unique = np.unique(values)
    return [{"x": float(x), "p_ge_x": float(np.mean(values >= x))} for x in unique]


def main() -> None:
    semantic_bytes = (DATA / "semantic_space.json").read_bytes()
    cards_bytes = (DATA / "heart_l4_risk_cards.json").read_bytes()
    semantic = json.loads(semantic_bytes)
    cards = json.loads(cards_bytes)
    card_by_id = {card["L4_ID"]: card for card in cards}
    point_by_id = {point["id"]: point for point in semantic["points"]}

    neighbors = {card_id: [] for card_id in point_by_id}
    for source, target, weight in semantic["edges"]:
        neighbors[source].append((target, float(weight)))
        neighbors[target].append((source, float(weight)))

    degree = np.array([point["degree"] for point in semantic["points"]], dtype=int)
    strength = np.array([point["strength"] for point in semantic["points"]], dtype=float)
    degree_fit = fit_discrete(degree)
    strength_fit = fit_continuous(strength)
    degree_fit["bootstrap_p"] = bootstrap_p(degree, degree_fit, True)
    strength_fit["bootstrap_p"] = bootstrap_p(strength, strength_fit, False)
    degree_fit.update(truncated_lognormal_comparison(degree, degree_fit, True))
    strength_fit.update(truncated_lognormal_comparison(strength, strength_fit, False))

    rankings = []
    for point in semantic["points"]:
        card = card_by_id[point["id"]]
        neighbor_domains = {"General AI": 0, "Agentic AI": 0, "Physical AI": 0}
        cross_domain_edges = 0
        for neighbor_id, _ in neighbors[point["id"]]:
            neighbor_domain = card_by_id[neighbor_id]["L1_Name_en"]
            neighbor_domains[neighbor_domain] += 1
            cross_domain_edges += neighbor_domain != card["L1_Name_en"]
        rankings.append({
            "id": point["id"], "name_en": card["L4_Name_en"], "name_ko": card["L4_Name_ko"],
            "l1_id": card["L1_ID"], "l1_name": card["L1_Name_en"], "l3_id": card["L3_ID"],
            "l3_name": card["L3_Name_en"], "degree": int(point["degree"]),
            "strength": float(point["strength"]), "neighbor_domains": neighbor_domains,
            "cross_domain_edges": int(cross_domain_edges),
            "cross_domain_share": float(cross_domain_edges / point["degree"]),
            "domains_reached": int(sum(value > 0 for value in neighbor_domains.values())),
        })
    rankings.sort(key=lambda item: (-item["degree"], -item["strength"], item["id"]))

    total_edges = len(semantic["edges"])
    cross_edges = sum(card_by_id[a]["L1_ID"] != card_by_id[b]["L1_ID"] for a, b, _ in semantic["edges"])
    l1_pairs: dict[str, int] = {}
    for a, b, _ in semantic["edges"]:
        pair = " ↔ ".join(sorted([card_by_id[a]["L1_Name_en"], card_by_id[b]["L1_Name_en"]]))
        l1_pairs[pair] = l1_pairs.get(pair, 0) + 1

    result = {
        "schema_version": "1.0",
        "generated_date": "2026-10-21",
        "analysis_unit": "L4 risk cards",
        "node_count": len(semantic["points"]),
        "edge_count": total_edges,
        "graph_rule": semantic["method"]["edge_rule"],
        "source": {
            "semantic_space_sha256": hashlib.sha256(semantic_bytes).hexdigest(),
            "risk_cards_sha256": hashlib.sha256(cards_bytes).hexdigest(),
            "embedding_sha256": semantic["method"]["embedding_sha256"],
            "taxonomy_source_sha256": semantic["source_sha256"],
        },
        "settings": {"seed": SEED, "bootstrap_replicates": BOOTSTRAPS, "minimum_tail_n": MIN_TAIL},
        "degree": {"measurement": "incident semantic links", "ccdf": ccdf(degree), **degree_fit},
        "strength": {"measurement": "sum of incident cosine-similarity weights", "ccdf": ccdf(strength), **strength_fit},
        "cross_domain": {
            "edge_count": int(cross_edges), "edge_share": float(cross_edges / total_edges),
            "within_domain_edge_count": int(total_edges - cross_edges),
            "l1_pair_counts": dict(sorted(l1_pairs.items())),
        },
        "rankings": rankings,
        "interpretation_rule": (
            "A bootstrap p-value below 0.10 rejects the fitted power-law tail. Otherwise the power law is not rejected, "
            "but it is not established unless the tail is substantial and alternatives are disfavored. A positive "
            "likelihood ratio favors the power law; a negative ratio favors the truncated lognormal."
        ),
        "limitations": [
            "The graph is a semantic k-nearest-neighbor construction, not an observed causal or temporal network.",
            "The union-of-eight-neighbors rule mechanically constrains the lower degree distribution.",
            "Results depend on risk-card wording, BGE-M3 embeddings, cosine threshold, and retained taxonomy inventory.",
            "Network centrality does not measure probability, severity, impact, or regulatory priority.",
        ],
    }
    (DATA / "scale_law_diagnostics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    with (DATA / "scale_law_top_l4.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rank", "L4_ID", "L4_Name_en", "L4_Name_ko", "L1_Name_en",
                                                        "L3_ID", "L3_Name_en", "degree", "strength",
                                                        "cross_domain_edges", "cross_domain_share", "domains_reached"])
        writer.writeheader()
        for rank, item in enumerate(rankings, 1):
            writer.writerow({"rank": rank, "L4_ID": item["id"], "L4_Name_en": item["name_en"],
                             "L4_Name_ko": item["name_ko"], "L1_Name_en": item["l1_name"],
                             "L3_ID": item["l3_id"], "L3_Name_en": item["l3_name"],
                             "degree": item["degree"], "strength": f'{item["strength"]:.6f}',
                             "cross_domain_edges": item["cross_domain_edges"],
                             "cross_domain_share": f'{item["cross_domain_share"]:.6f}',
                             "domains_reached": item["domains_reached"]})
    print(json.dumps({"degree": degree_fit, "strength": strength_fit,
                      "cross_domain": result["cross_domain"], "top10": rankings[:10]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
