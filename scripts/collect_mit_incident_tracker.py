#!/usr/bin/env python3
"""Download MIT AI Incident Tracker records from its public chart API.

The list endpoint supplies the authoritative ID inventory. Detail requests are
cached one JSON file per incident so interrupted runs resume without refetching.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://airi-echarts-visualizations.vercel.app/api/data/incidents"


def fetch_json(url: str, attempts: int = 5) -> dict:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HEART-research/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except Exception as exc:  # network failures are retried and surfaced
            error = exc
            time.sleep(min(8, 2**attempt))
    raise RuntimeError(f"Failed after {attempts} attempts: {url}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    detail_dir = args.out / "details"
    detail_dir.mkdir(exist_ok=True)

    list_url = API + "?" + urllib.parse.urlencode(
        {"src": "incidents-arcola", "chartType": "incident-list"}
    )
    inventory = fetch_json(list_url)
    (args.out / "incident-list.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ids = [str(item["incidentId"]) for item in inventory["items"]]

    def collect(incident_id: str) -> tuple[str, bool]:
        target = detail_dir / f"{incident_id}.json"
        if target.exists() and target.stat().st_size > 100:
            return incident_id, False
        url = API + "?" + urllib.parse.urlencode(
            {
                "src": "incidents-arcola",
                "chartType": "incident-detail",
                "incidentId": incident_id,
            }
        )
        payload = fetch_json(url)
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return incident_id, True

    downloaded = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(collect, incident_id) for incident_id in ids]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            _, changed = future.result()
            downloaded += int(changed)
            if index % 100 == 0 or index == len(ids):
                print(f"checked={index}/{len(ids)} downloaded={downloaded}", flush=True)

    records = []
    for incident_id in sorted(ids, key=int):
        payload = json.loads((detail_dir / f"{incident_id}.json").read_text(encoding="utf-8"))
        record = payload.get("incident")
        if not record or str(record.get("incidentId")) != incident_id:
            raise ValueError(f"Invalid detail payload for incident {incident_id}")
        records.append(record)
    with (args.out / "mit_incident_tracker.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote={len(records)} records")


if __name__ == "__main__":
    main()
