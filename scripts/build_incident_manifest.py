#!/usr/bin/env python3
"""Create a hash-addressed provenance manifest for public incident outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/incidents"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = [path for path in DATA.rglob("*") if path.is_file() and path.name != "manifest.json"]
    manifest = {
        "schema_version": "1.0",
        "created_at": "2026-10-21",
        "analytical_grain": {
            "source_records": "one row per source record",
            "canonical_incidents": "AIID identity is canonical when exact ID linkage exists; MIT is an AIID enrichment",
            "mapping_edges": "one row per incident-card candidate; five per event, top three flagged",
        },
        "sources": [
            {
                "name": "OECD AI Incidents Monitor",
                "url": "https://oecd.ai/en/incidents",
                "snapshot": "2026-08-24",
                "selection": "AI incident only; AI hazards excluded",
                "license_note": "OECD.AI terms; linked article content retains source rights",
            },
            {
                "name": "AI Incident Database",
                "url": "https://incidentdatabase.ai/research/snapshots/",
                "snapshot": "backup-20261019101022.tar.bz2",
                "license_note": "Database CC BY-SA 4.0; report contents retain source rights",
            },
            {
                "name": "MIT AI Incident Tracker",
                "url": "https://airisk.mit.edu/ai-incident-tracker",
                "snapshot": "2026-10-21",
                "license_note": "MIT site CC BY 4.0; underlying AIID records CC BY-SA 4.0",
            },
        ],
        "taxonomy": {
            "name": "HEART AI Risk Taxonomy",
            "cards": 622,
            "mapping_model": "bge-m3:latest",
            "model_digest": "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab",
            "validation": {
                "primary_release": "model-based; not human validated",
                "noncircular_remapping": "title, incident narrative and AI-system description only; source labels held out",
                "human_sample": "150-case stratified sheet frozen; adjudication pending",
                "embodied_audit": "100-case rule-audit sheet frozen; adjudication pending",
            },
        },
        "files": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(files)
        ],
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest files={len(files)}")


if __name__ == "__main__":
    main()
