#!/usr/bin/env python3
"""Build the canonical HEART L4 risk-card dataset from preserved masters."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HIERARCHY_ROOT = REPO / "source_snapshot"
EVIDENCE_LEDGER = HIERARCHY_ROOT / "L4_Golden_Reference_Ledger.csv"

SOURCES = {
    "General AI": HIERARCHY_ROOT / "General_AI_Risk_L4_Master.csv",
    "Agentic AI": HIERARCHY_ROOT / "Agentic_AI_Risk_L4_Master.csv",
    "Physical AI": HIERARCHY_ROOT / "Physical_AI_Risk_L4_Master.csv",
}

URL_OVERRIDES = {
    "https://aiverifyfoundation.sg/downloads/Cataloguing_LLM_Evaluations.pdf":
        "https://aiverifyfoundation.sg/wp-content/uploads/2025/10/Cataloguing_LLM_Evaluations.pdf",
}

FIELDS = [
    "L4_ID",
URL_OVERRIDES.update(json.loads((REPO / "data/evidence_pdf_url_map.json").read_text(encoding="utf-8")))
    "L4_Name_en",
    "L4_Name_ko",
    "L1_ID",
    "L1_Name_en",
    "L1_Name_ko",
    "L2_ID",
    "L2_Name_en",
    "L2_Name_ko",
    "L3_ID",
    "L3_Name_en",
    "L3_Name_ko",
    "Risk_Definition_en",
    "Risk_Definition_ko",
    "Facet",
    "Act_Type",
    "Evidence_Reference_Title",
    "Evidence_Reference_Authors",
    "Evidence_Reference_Year",
    "Evidence_Reference_Type",
    "Evidence_DOI",
    "Evidence_URL",
    "Evidence_Quote",
    "Evidence_Quote_Location",
    "Evidence_Source_ID",
    "Evidence_Source_Quality_Tier",
    "Evidence_Verification_Status",
    "Evidence_Accessed_At",
    "Probability",
    "Severity",
]


def clean(value: object) -> str:
    text = "" if value is None else str(value)
    return "" if text.strip().replace("\u00a0", "") == "" else text.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build() -> tuple[list[dict[str, str]], dict[str, object]]:
    evidence_rows = read_csv(EVIDENCE_LEDGER)
    evidence = {clean(row["L4_ID"]): row for row in evidence_rows}
    if len(evidence) != len(evidence_rows):
        raise ValueError("Evidence ledger contains duplicate L4 IDs")

    cards: list[dict[str, str]] = []
    domain_counts: Counter[str] = Counter()
    for domain, source in SOURCES.items():
        for row in read_csv(source):
            l4_id = clean(row["L4_ID"])
            ref = evidence.get(l4_id)
            if ref is None:
                raise KeyError(f"No evidence record for {l4_id}")
            card = {
                "L4_ID": l4_id,
                "L4_Name_en": clean(row["L4_Title_en"]),
                "L4_Name_ko": clean(row["L4_Title_ko"]),
                "L1_ID": clean(row["L1_ID"]),
                "L1_Name_en": clean(row["L1_Title_en"]),
                "L1_Name_ko": clean(row["L1_Title_ko"]),
                "L2_ID": clean(row["L2_ID"]),
                "L2_Name_en": clean(row["L2_Title_en"]),
                "L2_Name_ko": clean(row["L2_Title_ko"]),
                "L3_ID": clean(row["L3_ID"]),
                "L3_Name_en": clean(row["L3_Title_en"]),
                "L3_Name_ko": clean(row["L3_Title_ko"]),
                "Risk_Definition_en": clean(row["L4_Description_en"]),
                "Risk_Definition_ko": clean(row["L4_Description_ko"]),
                "Facet": clean(row.get("facet")),
                "Act_Type": clean(row.get("act-type")),
                "Evidence_Reference_Title": clean(ref["ref_title"]),
                "Evidence_Reference_Authors": clean(ref["ref_authors"]),
                "Evidence_Reference_Year": clean(ref["ref_year"]),
                "Evidence_Reference_Type": clean(ref["reference_type"]),
                "Evidence_DOI": clean(ref["doi"]),
                "Evidence_URL": URL_OVERRIDES.get(clean(ref["ref_url"]), clean(ref["ref_url"])),
                "Evidence_Quote": clean(ref["direct_quote"]),
                "Evidence_Quote_Location": clean(ref["quote_location"]),
                "Evidence_Source_ID": clean(ref["source_ev_id"]),
                "Evidence_Source_Quality_Tier": clean(ref["source_quality_tier"]),
                "Evidence_Verification_Status": clean(ref["verification_status"]),
                "Evidence_Accessed_At": clean(ref["accessed_at"]),
                "Probability": "",
                "Severity": "",
            }
            missing = [
                field
                for field in (
                    "L4_ID",
                    "L4_Name_en",
                    "L4_Name_ko",
                    "L1_ID",
                    "L2_ID",
                    "L3_ID",
                    "Risk_Definition_en",
                    "Risk_Definition_ko",
                    "Evidence_Reference_Title",
                    "Evidence_URL",
                    "Evidence_Quote",
                )
                if not card[field]
            ]
            if missing:
                raise ValueError(f"{l4_id} missing required fields: {missing}")
            if card["L3_ID"] != clean(ref["L3_ID"]):
                raise ValueError(f"L3 mismatch for {l4_id}")
            cards.append(card)
            domain_counts[domain] += 1

    cards.sort(key=lambda row: (row["L1_ID"], row["L3_ID"], row["L4_ID"]))
    ids = [row["L4_ID"] for row in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("Canonical dataset contains duplicate L4 IDs")
    if len(cards) != 622:
        raise ValueError(f"Expected 622 cards, found {len(cards)}")
    if any(row["Probability"] or row["Severity"] for row in cards):
        raise ValueError("Probability and Severity must remain blank")

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = {
        "dataset_name": "HEART L4 Risk Card Dataset",
        "taxonomy_name": "HEART: Hybrid Evidence-based AI Risk Taxonomy",
        "schema_version": "1.0.0",
        "generated_at_utc": generated,
        "card_count": len(cards),
        "l3_count": len({row["L3_ID"] for row in cards}),
        "domain_counts": dict(domain_counts),
        "language": "English primary with Korean parallel fields",
        "probability_status": "Reserved field; values intentionally blank",
        "severity_status": "Reserved field; values intentionally blank",
        "human_review_workflow_included": False,
        "evidence_coverage": {
            "references": sum(bool(row["Evidence_Reference_Title"]) for row in cards),
            "urls": sum(bool(row["Evidence_URL"]) for row in cards),
            "direct_quotes": sum(bool(row["Evidence_Quote"]) for row in cards),
        },
    }
    return cards, manifest


def main() -> None:
    cards, manifest = build()
    repo_csv = REPO / "data" / "heart_l4_risk_cards.csv"
    repo_json = REPO / "data" / "heart_l4_risk_cards.json"
    write_csv(repo_csv, cards)
    repo_json.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest["files"] = {
        "csv": {"path": repo_csv.name, "sha256": sha256(repo_csv)},
        "json": {"path": repo_json.name, "sha256": sha256(repo_json)},
    }
    manifest_path = REPO / "data" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
