#!/usr/bin/env python3
"""Synchronise the public HEART site with the validated 55-L3 master."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ID_MAP = {
    "P_SYS_CONTROL_040": "P_SYS_TIMESYNC_003",
    "A_SYS_AUTH_020": "A_SYS_RESOURCE_001",
    "P_INT_SAFETY_012": "P_SYS_TASKPLAN_003",
    "G_SYS_PERF_015": "P_INT_OBSTRUCT_001",
    "A_SYS_SELFCOR_002": "A_SYS_MEMSTATE_001",
    "A_SYS_AUTH_004": "A_INT_OVERSIGHT_001",
    "P_SYS_CONTROL_034": "P_SYS_TIMESYNC_002",
    "A_SYS_AUTH_007": "A_INT_OVERSIGHT_002",
    "A_SYS_GOAL_020": "A_SYS_EXEC_001",
    "P_SYS_CONTROL_007": "P_SYS_TIMESYNC_001",
    "P_SYS_CONTROL_044": "P_SYS_SAFESTATE_002",
    "P_SYS_CONTROL_052": "P_SYS_TASKPLAN_002",
    "P_SYS_CONTROL_016": "P_SYS_TASKPLAN_001",
    "P_SYS_CONTROL_042": "P_SYS_SAFESTATE_001",
    "A_SYS_AUTH_023": "A_SYS_EXEC_002",
}

BASE_COLOURS = {"L1_G": "#4263eb", "L1_A": "#d87518", "L1_P": "#00977e"}


def remap(value):
    if isinstance(value, dict):
        return {key: remap(item) for key, item in value.items()}
    if isinstance(value, list):
        return [remap(item) for item in value]
    if isinstance(value, str):
        for old, new in ID_MAP.items():
            value = value.replace(old, new)
        return value
    return value


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_npz_deterministic(path: Path, arrays: dict) -> None:
    """Write an NPZ with fixed metadata so identical arrays give identical bytes."""
    temporary = path.with_suffix(".sync.npz")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, array in arrays.items():
            payload = io.BytesIO()
            np.lib.format.write_array(payload, np.asanyarray(array), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    temporary.replace(path)


def main() -> None:
    cards_path = DATA / "heart_l4_risk_cards.json"
    cards_raw = cards_path.read_bytes()
    cards = json.loads(cards_raw)
    by_id = {card["L4_ID"]: card for card in cards}
    assert len(cards) == len(by_id) == 622
    assert len({card["L3_ID"] for card in cards}) == 55
    assert Counter(card["L1_Name_en"] for card in cards) == {
        "General AI": 491,
        "Agentic AI": 67,
        "Physical AI": 64,
    }
    source_hash = hashlib.sha256(cards_raw).hexdigest()

    embedding_path = DATA / "semantic_embeddings.npz"
    with np.load(embedding_path, allow_pickle=False) as archive:
        embedding_arrays = {name: archive[name] for name in archive.files}
    embedding_arrays["ids"] = np.array([remap(str(item)) for item in embedding_arrays["ids"]])
    assert set(embedding_arrays["ids"].tolist()) == set(by_id)
    write_npz_deterministic(embedding_path, embedding_arrays)
    embedding_hash = hashlib.sha256(embedding_path.read_bytes()).hexdigest()

    semantic_path = DATA / "semantic_space.json"
    semantic = remap(json.loads(semantic_path.read_text(encoding="utf-8")))
    point_by_id = {point["id"]: point for point in semantic["points"]}
    assert set(point_by_id) == set(by_id)
    for point_id, point in point_by_id.items():
        point["cluster"] = by_id[point_id]["L3_ID"]
    semantic["source_sha256"] = source_hash
    semantic["method"]["embedding_sha256"] = embedding_hash
    scenario_domains = {
        "ai-for-everyone": {"L1_G", "L1_A"},
        "legal-assistance": {"L1_G", "L1_A"},
        "financial-chatbots": {"L1_G"},
        "financial-ai-agent": {"L1_G", "L1_A"},
    }
    for scenario in semantic["scenarios"]:
        allowed = scenario_domains[scenario["id"]]
        scenario["ids"] = [risk_id for risk_id in scenario["ids"] if by_id[risk_id]["L1_ID"] in allowed]
    domain_keywords = {"general-ai": "L1_G", "agentic-ai": "L1_A", "physical-ai": "L1_P"}
    for keyword in semantic["keywords"]:
        if keyword["id"] in domain_keywords:
            domain = domain_keywords[keyword["id"]]
            keyword["ids"] = [card["L4_ID"] for card in cards if card["L1_ID"] == domain]

    prior_categories = {item["L3_ID"]: item for item in semantic["clusters"]}
    categories = []
    for l3_id in sorted({card["L3_ID"] for card in cards}):
        members = [card for card in cards if card["L3_ID"] == l3_id]
        first = members[0]
        points = [point_by_id[card["L4_ID"]] for card in members]
        template = dict(prior_categories.get(l3_id, {}))
        template.update(
            {
                "L1_ID": first["L1_ID"],
                "L1_Title_en": first["L1_Name_en"],
                "L2_ID": first["L2_ID"],
                "L2_Title_en": first["L2_Name_en"],
                "L3_ID": l3_id,
                "L3_Title_en": first["L3_Name_en"],
                "L3_Description_en": "",
                "color": template.get("color", BASE_COLOURS[first["L1_ID"]]),
                "gradient_start": template.get("gradient_start", BASE_COLOURS[first["L1_ID"]]),
                "gradient_end": template.get("gradient_end", BASE_COLOURS[first["L1_ID"]]),
                "id": l3_id,
                "name": first["L3_Name_en"],
                "label": first["L3_Name_en"],
                "x": sum(point["x"] for point in points) / len(points),
                "y": sum(point["y"] for point in points) / len(points),
                "ids": [card["L4_ID"] for card in members],
            }
        )
        categories.append(template)
    semantic["clusters"] = categories
    semantic["l1_colors"] = BASE_COLOURS
    semantic["method"]["taxonomy_sync"] = (
        "55 human-validated L3 categories; 622 L4 cards; graph coordinates and edges preserved "
        "for unchanged risk texts, with the validated ID migration applied."
    )
    write_json(semantic_path, semantic)

    l3_path = DATA / "l3_semantic_colours.json"
    l3 = remap(json.loads(l3_path.read_text(encoding="utf-8")))
    l3["source_sha256"] = source_hash
    l3["categories"] = [
        {key: value for key, value in category.items() if key not in {"id", "name", "label", "x", "y", "ids"}}
        for category in categories
    ]
    l3["limitations"] = (
        "Category colours are navigational aids. They do not represent distance, confidence, "
        "severity, likelihood, or a change to the human-validated hierarchy."
    )
    write_json(l3_path, l3)

    l4_path = DATA / "l4_semantic_colours.json"
    l4 = remap(json.loads(l4_path.read_text(encoding="utf-8")))
    l4["source_sha256"] = source_hash
    l4["l3_palette_sha256"] = hashlib.sha256(l3_path.read_bytes()).hexdigest()
    assert {point["id"] for point in l4["points"]} == set(by_id)
    for point in l4["points"]:
        point["l3"] = by_id[point["id"]]["L3_ID"]
    write_json(l4_path, l4)

    definition_paths = [
        DATA / "keyword_definitions.json",
        DATA / "keyword_review/keyword_mapping_review_a.json",
        DATA / "keyword_review/keyword_mapping_review_b.json",
    ]
    for path in definition_paths:
        write_json(path, remap(json.loads(path.read_text(encoding="utf-8"))))

    keyword_path = DATA / "keyword_semantics.json"
    keyword = remap(json.loads(keyword_path.read_text(encoding="utf-8")))
    keyword["source_sha256"] = source_hash
    keyword["definitions_sha256"] = hashlib.sha256((DATA / "keyword_definitions.json").read_bytes()).hexdigest()
    for item in keyword["keywords"]:
        if item["id"] in domain_keywords:
            domain = domain_keywords[item["id"]]
            item["ids"] = [card["L4_ID"] for card in cards if card["L1_ID"] == domain]
    write_json(keyword_path, keyword)

    mapping_path = DATA / "financial_ai_agent_heart_l4_mapping_final.csv"
    with mapping_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = handle.seek(0) or list(rows[0])
    fieldnames = list(rows[0])
    for row in rows:
        if row["l4_id"] in ID_MAP:
            row["l4_id"] = ID_MAP[row["l4_id"]]
        if row["l4_id"]:
            card = by_id[row["l4_id"]]
            row.update(
                l4_name_ko=card["L4_Name_ko"],
                l4_name_en=card["L4_Name_en"],
                l4_definition_ko=card["Risk_Definition_ko"],
                l4_definition_en=card["Risk_Definition_en"],
                l1_id=card["L1_ID"],
                l2_id=card["L2_ID"],
                l3_id=card["L3_ID"],
            )
    with mapping_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    assert len(categories) == 55
    assert all(point["cluster"] in {item["id"] for item in categories} for point in semantic["points"])
    print(json.dumps({"cards": 622, "l3_categories": 55, "migrated_ids": len(ID_MAP)}, indent=2))


if __name__ == "__main__":
    main()
