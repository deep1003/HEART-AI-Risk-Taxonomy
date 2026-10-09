#!/usr/bin/env python3
"""Validate the HEART release and refresh evidence URL accessibility records."""

from __future__ import annotations

import csv
import json
import ssl
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "heart_l4_risk_cards.csv"
URL_AUDIT = ROOT / "data" / "evidence_url_audit.csv"
REPORT = ROOT / "data" / "validation.json"


def probe(url: str) -> dict[str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 HEART-evidence-validator/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            status = response.status
            resolved = response.geturl()
            content_type = response.headers.get("content-type", "")
            result = "reachable" if 200 <= status < 400 else "unexpected"
    except urllib.error.HTTPError as error:
        status = error.code
        resolved = error.geturl()
        content_type = error.headers.get("content-type", "") if error.headers else ""
        result = "access_controlled" if status in {401, 403, 429} else "http_error"
    except Exception as error:
        status = ""
        resolved = ""
        content_type = ""
        result = f"network_error:{type(error).__name__}"
    return {
        "url": url,
        "result": result,
        "http_status": str(status),
        "resolved_url": resolved,
        "content_type": content_type,
    }


def main() -> None:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["L4_ID"] for row in rows]
    required = [
        "L4_ID", "L4_Name_en", "L4_Name_ko", "L1_ID", "L2_ID", "L3_ID",
        "Risk_Definition_en", "Risk_Definition_ko", "Evidence_Reference_Title",
        "Evidence_URL", "Evidence_Quote",
    ]
    missing_required = [row["L4_ID"] for row in rows if any(not row[field].strip() for field in required)]
    urls = sorted({row["Evidence_URL"].strip() for row in rows})
    with ThreadPoolExecutor(max_workers=8) as executor:
        checks = list(executor.map(probe, urls))
    with URL_AUDIT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows(checks)
    results = Counter(row["result"].split(":", 1)[0] for row in checks)
    report = {
        "validated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "card_count": len(rows),
        "unique_l4_ids": len(set(ids)),
        "l3_count": len({row["L3_ID"] for row in rows}),
        "domain_counts": dict(Counter(row["L1_Name_en"] for row in rows)),
        "missing_required_rows": missing_required,
        "probability_nonblank": sum(bool(row["Probability"].strip()) for row in rows),
        "severity_nonblank": sum(bool(row["Severity"].strip()) for row in rows),
        "distinct_evidence_urls": len(urls),
        "url_results": dict(results),
        "passed_structural_validation": (
            len(rows) == 622
            and len(set(ids)) == 622
            and len({row["L3_ID"] for row in rows}) == 47
            and not missing_required
            and not any(row["Probability"].strip() or row["Severity"].strip() for row in rows)
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed_structural_validation"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
