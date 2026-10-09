#!/usr/bin/env python3
"""Build a reproducible text projection and overlapping scenario lenses.

The canonical cards are read-only. Scenario relevance is editorial, conditional
applicability, not an observed incident, severity estimate or taxonomy reassignment.
Requires NumPy and scikit-learn; no remote model, service, or synthetic coordinates are used.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import sklearn
from sklearn.manifold import TSNE, trustworthiness

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "heart_l4_risk_cards.json"
STOP = set("""a an the and or of to in on for by from with without as at is are be been
that this these those it its their them they which who whose when where while such
through into over under than each any other both also only not can could may might
will would should must has have had do does did more most less some all including
include includes e.g example examples resulting result results creates create condition
causes cause causing due leads lead leading risk risks ai system systems algorithm
algorithms model models artificial intelligence enabled learning technology technologies
failure failures harmful harm harms beyond within across during using use uses used
design deployment training process processes information content actions action decisions
decision behaviour behaviors behavior capabilities capability otherwise individuals people
groups particular specific actual appropriate inappropriate necessary""".split())

SCENARIOS = [
    {"id": "delivery-robots", "name": "Delivery robot services", "name_ko": "배달로봇서비스",
     "description": "Mobile robots sharing pavements, entrances and public spaces with pedestrians. Includes fleet connectivity and public-space access.",
     "ids": """P_INT_SAFETY_005 P_INT_SAFETY_006 P_INT_SAFETY_007 P_INT_SAFETY_009
     P_INT_SAFETY_010 P_INT_SAFETY_012 P_INT_SAFETY_015 P_INT_SAFETY_017 P_INT_SAFETY_020
     P_INT_TAMPER_002 P_INT_TAMPER_003 P_SYS_CONTROL_002 P_SYS_CONTROL_006
     P_SYS_CONTROL_007 P_SYS_CONTROL_012 P_SYS_CONTROL_013 P_SYS_CONTROL_016
     P_SYS_CONTROL_017 P_SYS_CONTROL_019 P_SYS_CONTROL_022 P_SYS_CONTROL_034
     P_SYS_CONTROL_040 P_SYS_CONTROL_042 P_SYS_CONTROL_043 P_SYS_CONTROL_051
     P_SYS_CONTROL_052 P_SYS_CONTROL_054 P_SYS_CONTROL_057 P_SYS_HARDWARE_002
     P_SYS_HARDWARE_003 P_SYS_STATE_004 P_SYS_STATE_006 P_SYS_STATE_008 P_SYS_STATE_009
     P_SYS_STATE_011 G_INT_ALLOC_003 G_INT_PRIV_001 G_INT_PRIV_003 G_INT_PRIV_021
     G_INT_VALUE_020 G_SOC_GOV_039 G_SYS_PERF_015 G_SYS_EVAL_044 G_SYS_SECADV_015
     G_SYS_SECADV_058 A_SYS_AUTH_023 A_SYS_GOAL_016 A_SYS_TRACE_002""".split()},
    {"id": "factory-humanoids", "name": "Humanoids in factories", "name_ko": "공장의 휴머노이드",
     "description": "Humanoids working alongside people, manipulating tools and materials, and coordinating industrial tasks. Workplace monitoring is included conditionally.",
     "ids": """P_INT_SAFETY_001 P_INT_SAFETY_005 P_INT_SAFETY_006 P_INT_SAFETY_007
     P_INT_SAFETY_008 P_INT_SAFETY_009 P_INT_SAFETY_010 P_INT_SAFETY_011
     P_INT_SAFETY_012 P_INT_SAFETY_015 P_INT_SAFETY_016 P_INT_SAFETY_017
     P_INT_SAFETY_018 P_INT_SAFETY_021 P_INT_TAMPER_002 P_INT_TAMPER_003
     P_SYS_CONTROL_002 P_SYS_CONTROL_006 P_SYS_CONTROL_007 P_SYS_CONTROL_013
     P_SYS_CONTROL_015 P_SYS_CONTROL_016 P_SYS_CONTROL_017 P_SYS_CONTROL_018
     P_SYS_CONTROL_019 P_SYS_CONTROL_022 P_SYS_CONTROL_023 P_SYS_CONTROL_024
     P_SYS_CONTROL_025 P_SYS_CONTROL_026 P_SYS_CONTROL_027 P_SYS_CONTROL_030
     P_SYS_CONTROL_033 P_SYS_CONTROL_034 P_SYS_CONTROL_037 P_SYS_CONTROL_038
     P_SYS_CONTROL_040 P_SYS_CONTROL_042 P_SYS_CONTROL_043 P_SYS_CONTROL_044
     P_SYS_CONTROL_047 P_SYS_CONTROL_050 P_SYS_CONTROL_051 P_SYS_CONTROL_052
     P_SYS_CONTROL_054 P_SYS_CONTROL_055 P_SYS_CONTROL_056 P_SYS_CONTROL_057
     P_SYS_HARDWARE_002 P_SYS_HARDWARE_003 P_SYS_STATE_003 P_SYS_STATE_004
     P_SYS_STATE_006 P_SYS_STATE_007 P_SYS_STATE_008 P_SYS_STATE_009 P_SYS_STATE_011
     G_INT_ALLOC_003 G_INT_PRIV_002 G_INT_PRIV_030 G_INT_PRIV_031 G_SOC_ECON_002
     G_SOC_GOV_039 G_SYS_EVAL_044 G_SYS_SECADV_011 G_SYS_SECADV_016 G_SYS_SECADV_060
     A_SYS_AUTH_023 A_SYS_GOAL_016 A_SYS_GOAL_018 A_SYS_TRACE_002""".split()},
    {"id": "home-humanoids", "name": "Household assistant humanoids", "name_ko": "가사 도우미 휴머노이드",
     "description": "Humanoids assisting with domestic tasks around people, fragile objects and private spaces. Relationship-related risks apply when a conversational interface is provided.",
     "ids": """P_INT_SAFETY_001 P_INT_SAFETY_005 P_INT_SAFETY_006 P_INT_SAFETY_007
     P_INT_SAFETY_008 P_INT_SAFETY_009 P_INT_SAFETY_010 P_INT_SAFETY_011
     P_INT_SAFETY_012 P_INT_SAFETY_015 P_INT_SAFETY_016 P_INT_SAFETY_017
     P_INT_SAFETY_018 P_INT_SAFETY_020 P_INT_SAFETY_021 P_INT_SAFETY_023
     P_INT_TAMPER_002 P_SYS_CONTROL_002 P_SYS_CONTROL_006 P_SYS_CONTROL_007
     P_SYS_CONTROL_013 P_SYS_CONTROL_015 P_SYS_CONTROL_016 P_SYS_CONTROL_017
     P_SYS_CONTROL_018 P_SYS_CONTROL_019 P_SYS_CONTROL_022 P_SYS_CONTROL_023
     P_SYS_CONTROL_024 P_SYS_CONTROL_025 P_SYS_CONTROL_026 P_SYS_CONTROL_027
     P_SYS_CONTROL_030 P_SYS_CONTROL_033 P_SYS_CONTROL_038 P_SYS_CONTROL_040
     P_SYS_CONTROL_042 P_SYS_CONTROL_043 P_SYS_CONTROL_046 P_SYS_CONTROL_047
     P_SYS_CONTROL_050 P_SYS_CONTROL_051 P_SYS_CONTROL_052 P_SYS_CONTROL_054
     P_SYS_CONTROL_055 P_SYS_CONTROL_056 P_SYS_CONTROL_057 P_SYS_HARDWARE_002
     P_SYS_HARDWARE_003 P_SYS_STATE_003 P_SYS_STATE_004 P_SYS_STATE_006
     P_SYS_STATE_007 P_SYS_STATE_008 P_SYS_STATE_009 P_SYS_STATE_011
     G_INT_ALLOC_003 G_INT_ANTH_002 G_INT_ANTH_006 G_INT_PRIV_007 G_INT_PRIV_018
     G_INT_PRIV_024 G_SOC_ECON_002 G_SOC_GOV_039 G_SYS_EVAL_033
     G_SYS_EVAL_044 G_SYS_SECADV_011 G_SYS_SECADV_058 G_SYS_SECADV_060
     A_SYS_AUTH_023 A_SYS_GOAL_016 A_SYS_GOAL_018 A_SYS_TRACE_002""".split()},
    {"id": "network-agents", "name": "Autonomous network operations agents", "name_ko": "네트워크 장애 진단·자율 운영 에이전트",
     "description": "Software agents diagnosing faults, using operational tools and changing network configurations. Multi-agent risks apply when operators deploy collaborating agents.",
     "prefixes": ["A_SYS_AUTH", "A_SYS_GOAL", "A_SYS_SELFCOR", "A_SYS_TRACE", "A_INT_COORD", "A_INT_CASCADE"],
     "exclude": ["A_SYS_AUTH_007", "A_SYS_AUTH_010", "A_SYS_AUTH_024", "A_SYS_GOAL_007", "A_INT_CASCADE_005"],
     "ids": """G_SYS_CONTEXT_001 G_SYS_CONTEXT_002 G_SYS_INPUT_001 G_SYS_INPUT_002
     G_SYS_INCONS_001 G_SYS_POLICY_006 G_SYS_POLICY_010 G_SYS_SECADV_005
     G_SYS_SECADV_023 G_SYS_SECADV_044 G_SYS_SECADV_057 G_SYS_TRANS_002
     G_SYS_MISINFO_002 G_SOC_GOV_044 G_SYS_EVAL_069""".split()},
]

TOPICS = [
    {"id": "misuse", "name": "Misuse", "prefixes": ["G_INT_ILLEGAL", "G_INT_WEAP"], "terms": ["misuse", "malicious use", "malicious actor", "criminal", "fraud", "abuse of", "weaponiz", "weaponis"]},
    {"id": "mis-disinformation", "name": "Mis/disinformation", "prefixes": ["G_SYS_MISINFO"], "terms": ["misinformation", "disinformation", "false information", "fake news", "deepfake"]},
    {"id": "hate-unfairness", "name": "Hate and unfairness", "prefixes": ["G_INT_ALLOC", "G_INT_REPR"], "terms": ["hate speech", "hateful", "discriminat", "unfair"]},
    {"id": "self-harm", "name": "Self-harm", "prefixes": ["G_INT_SELF"], "terms": ["self-harm", "suicide", "suicidal"]},
    {"id": "security", "name": "Cybersecurity", "prefixes": ["G_SYS_SECADV", "P_INT_TAMPER"], "ids": ["A_SYS_AUTH_001", "A_SYS_AUTH_005", "A_SYS_AUTH_025"]},
    {"id": "democracy", "name": "Democracy", "prefixes": ["G_SOC_DEMOC", "G_INT_POL"], "terms": ["democra", "election", "voting", "civic"]},
    {"id": "education", "name": "Education", "terms": ["education", "educational", "school", "student", "classroom", "academic", "pedagog", "learning outcomes"]},
    {"id": "labour", "name": "Labour", "prefixes": ["G_SOC_ECON"], "terms": ["labour", "labor market", "worker", "workplace", "employment", "wage", "job displacement"]},
    {"id": "human-rights", "name": "Human rights", "prefixes": ["G_INT_ALLOC", "G_INT_REPR", "G_INT_PRIV", "G_SYS_CONTEST"], "terms": ["human rights", "fundamental rights", "civil liberties", "freedom of", "human dignity"]},
    {"id": "out-of-control", "name": "Out of control", "prefixes": ["A_SYS_AUTH", "A_SYS_GOAL", "P_SYS_CONTROL"], "terms": ["loss of control", "uncontroll", "shutdown", "emergency stop", "runaway"]},
    {"id": "prompt-injection", "name": "Prompt injection", "terms": ["prompt injection", "prompt-injection", "instruction injection", "indirect injection"]},
    {"id": "human-robot-interaction", "name": "Human-robot interaction", "prefixes": ["P_INT_SAFETY"], "terms": ["human-robot", "human robot", "human–robot", "robot-human", "collaborative robot", "human proximity", "physical interaction"]},
]


def tokens(card):
    text = f"{card['L4_Name_en']} {card['L4_Name_en']} {card['Risk_Definition_en']}"
    words = [word for word in re.findall(r"[a-z]{3,}", text.lower()) if word not in STOP]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


def match(card, rule):
    text = (card["L4_Name_en"] + " " + card["Risk_Definition_en"]).lower()
    if rule.get("domains") and card["L1_ID"] not in rule["domains"]:
        return False
    return (card["L4_ID"] in rule.get("ids", [])
            or any(card["L4_ID"].startswith(prefix + "_") for prefix in rule.get("prefixes", []))
            or any(term in text for term in rule.get("terms", [])))


def main():
    raw = SOURCE.read_bytes()
    cards = sorted(json.loads(raw), key=lambda card: card["L4_ID"])
    ids = {card["L4_ID"] for card in cards}
    counts = [Counter(tokens(card)) for card in cards]
    df = Counter(token for count in counts for token in count)
    vocab = sorted(token for token, n in df.items() if 2 <= n <= len(cards) * .75)
    lookup = {token: index for index, token in enumerate(vocab)}
    matrix = np.zeros((len(cards), len(vocab)))
    for row, count in enumerate(counts):
        for token, n in count.items():
            if token in lookup:
                matrix[row, lookup[token]] = (1 + np.log(n)) * (1 + np.log((1 + len(cards)) / (1 + df[token])))
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    cosine = matrix @ matrix.T
    centred = matrix - matrix.mean(axis=0)
    values, vectors = np.linalg.eigh(centred @ centred.T)
    order = np.argsort(values)[::-1]
    values, vectors = np.maximum(values[order], 0), vectors[:, order]
    latent = vectors[:, :48] * np.sqrt(values[:48])
    # Fix eigenvector sign deterministically; coordinates are never scenario-dependent.
    for axis in range(latent.shape[1]):
        if latent[np.argmax(np.abs(latent[:, axis])), axis] < 0:
            latent[:, axis] *= -1
    unit = latent / np.maximum(np.linalg.norm(latent, axis=1, keepdims=True), 1e-12)
    coordinates = TSNE(n_components=2, perplexity=35, init="pca", learning_rate="auto",
                       max_iter=1200, random_state=23, metric="cosine", n_jobs=1).fit_transform(unit)
    neighbourhood_preservation = trustworthiness(unit, coordinates, n_neighbors=10, metric="cosine")
    chosen = [int(np.random.default_rng(23).integers(len(cards)))]
    for _ in range(11):
        distance = np.min(np.sum((unit[:, None, :] - unit[chosen][None, :, :]) ** 2, axis=2), axis=1)
        chosen.append(int(np.argmax(distance)))
    centres = unit[chosen].copy()
    for _ in range(100):
        labels = np.argmin(np.sum((unit[:, None, :] - centres[None, :, :]) ** 2, axis=2), axis=1)
        next_centres = np.array([unit[labels == group].mean(axis=0) if np.any(labels == group) else centres[group]
                                 for group in range(12)])
        if np.allclose(centres, next_centres, atol=1e-8):
            break
        centres = next_centres
    clusters = []
    for group in range(12):
        mean = matrix[labels == group].mean(axis=0)
        terms = [vocab[index] for index in np.argsort(mean)[::-1] if " " not in vocab[index]][:3]
        clusters.append({"id": f"topic-{group}", "name": " · ".join(word.title() for word in terms),
                         "ids": [card["L4_ID"] for index, card in enumerate(cards) if labels[index] == group]})
    scenarios = []
    for rule in SCENARIOS:
        assert set(rule.get("ids", [])) <= ids, f"Unknown IDs in {rule['id']}"
        chosen_ids = [card["L4_ID"] for card in cards if match(card, rule) and card["L4_ID"] not in rule.get("exclude", [])]
        scenarios.append({key: rule[key] for key in ("id", "name", "name_ko", "description")} | {"ids": chosen_ids})
    topics = [{"id": rule["id"], "name": rule["name"],
               "ids": [card["L4_ID"] for card in cards if match(card, rule)]} for rule in TOPICS]
    edges = set()
    for index in range(len(cards)):
        for other in np.argsort(cosine[index])[-4:]:
            if index != other and cosine[index, other] >= .3:
                edges.add(tuple(sorted((int(index), int(other)))))
    result = {
        "schema_version": "1.0", "card_count": len(cards),
        "source_file": "heart_l4_risk_cards.json", "source_sha256": hashlib.sha256(raw).hexdigest(),
        "method": {"projection": "TF-IDF, centred PCA to 48 dimensions, cosine t-SNE to two dimensions", "clustering": "12 k-means topics in 48-dimensional text space",
                   "features": "English L4 name (double weight) and definition; unigrams and bigrams; log TF; smoothed IDF; L2 normalisation",
                   "scenario_membership": "Editorial, overlapping conditional applicability lenses; not an empirical incident classification",
                   "pca_48_variance_fraction": round(float(values[:48].sum() / values.sum()), 6),
                   "neighbourhood_trustworthiness_k10": round(float(neighbourhood_preservation), 6),
                   "random_seed": 23, "tsne_perplexity": 35, "tsne_iterations": 1200,
                   "numeric_backend": f"NumPy {np.__version__}, scikit-learn {sklearn.__version__}",
                   "edge_rule": "Up to three closest TF-IDF neighbours per card with cosine at least 0.30; ties may be fewer",
                   "limitations": "t-SNE emphasises local text neighbourhoods. Global distances, cluster areas and axis values have no risk meaning. Neighbours do not imply causation, likelihood, severity, or validated deployment-specific relevance."},
        "points": [{"id": card["L4_ID"], "x": round(float(coordinates[index, 0]), 7), "y": round(float(coordinates[index, 1]), 7),
                    "cluster": f"topic-{labels[index]}"} for index, card in enumerate(cards)],
        "edges": [[cards[a]["L4_ID"], cards[b]["L4_ID"]] for a, b in sorted(edges)],
        "clusters": clusters, "scenarios": scenarios, "keywords": topics,
    }
    assert len(result["points"]) == 622 and np.isfinite(latent).all()
    destination = ROOT / "data" / "semantic_space.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    assert SOURCE.read_bytes() == raw
    print(json.dumps({"points": len(cards), "features": len(vocab), "clusters": len(clusters),
                      "scenario_counts": {item["id"]: len(item["ids"]) for item in scenarios},
                      "neighbourhood_trustworthiness_k10": neighbourhood_preservation,
                      "source_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
