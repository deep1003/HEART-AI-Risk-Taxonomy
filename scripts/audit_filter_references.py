"""Verify display-reference access and document identity without changing mappings."""
import concurrent.futures
import hashlib
import io
import json
import re
import urllib.request
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def check_source(item):
    key, source = item
    record = {"id": key, "url": source["url"], "title": source["title"]}
    try:
        request = urllib.request.Request(source["url"], headers={"User-Agent": "Mozilla/5.0 HEART reference validation"})
        with urllib.request.urlopen(request, timeout=45) as response:
            content = response.read()
            record.update(status=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type", ""))
        if content.startswith(b"%PDF"):
            pdf = PdfReader(io.BytesIO(content))
            text = " ".join(page.extract_text() or "" for page in pdf.pages[:8])
            record["page_count"] = len(pdf.pages)
        else:
            text = re.sub(r"<[^>]*>", " ", content.decode("utf-8", errors="replace"))
        normalised = re.sub(r"[^\w]", "", unicodedata.normalize("NFKC", text).lower())
        expected = re.sub(r"[^\w]", "", unicodedata.normalize("NFKC", source["match"]).lower())
        record["identity_match"] = expected in normalised
        record["sha256"] = hashlib.sha256(content).hexdigest()
        record["verified"] = record["status"] == 200 and record["identity_match"]
        record["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    except Exception as error:
        record.update(verified=False, error=str(error))
    return record


def main():
    catalog = json.loads((ROOT / "data/filter_references.json").read_text())
    for item in catalog["filters"].values():
        assert len(set(item["references"])) >= 2
        assert set(item["references"]).issubset(catalog["sources"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(check_source, catalog["sources"].items()))
    browser_checks = json.loads((ROOT / "data/filter_reference_browser_checks.json").read_text())
    today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    for record in results:
        browser = browser_checks.get(record["id"], {})
        if (not record["verified"] and browser.get("verified") and
                browser.get("checked_date_kst") == today and
                browser.get("url") == record["url"] and browser.get("title") == record["title"]):
            record.update(verified=True, verification_channel="dated_browser_observation",
                          browser_check=browser, automated_http_verified=False)
    report = {"catalog_sha256": hashlib.sha256((ROOT / "data/filter_references.json").read_bytes()).hexdigest(),
              "method": "Direct HTTP GET; PDF parsing and title/concept identity check in the first eight pages, or HTML text identity check. An explicit same-day browser observation may verify a blocked automated request; its original error remains recorded. Relevance is separately adjudicated in each filter's support field. Access verification is a dated snapshot, not a permanence guarantee.",
              "results": results}
    (ROOT / "data/filter_reference_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    failures = [item for item in results if not item["verified"]]
    print(json.dumps({"checked": len(results), "verified": len(results)-len(failures), "failures": failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
