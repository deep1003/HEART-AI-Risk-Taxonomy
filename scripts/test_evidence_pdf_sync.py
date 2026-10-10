"""Read-only checks for evidence URL synchronisation and scope preservation."""
import csv
import hashlib
import json
from copy import copy
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MAPPING = json.loads((DATA / "evidence_pdf_url_map.json").read_text())
cards = json.loads((DATA / "heart_l4_risk_cards.json").read_text())
with (DATA / "heart_l4_risk_cards.csv").open(encoding="utf-8-sig", newline="") as handle:
    csv_cards = list(csv.DictReader(handle))
assert csv_cards == cards
workbook = openpyxl.load_workbook(DATA / "HEART_L4_Risk_Cards.xlsx")
sheet = workbook["Risk Cards"]
rows = list(sheet.values)
rows[0] = tuple(str(value).lstrip('\ufeff') for value in rows[0])
for row, card in zip(rows[1:], cards):
    for key, value in zip(rows[0], row):
        if isinstance(value, datetime):
            # Existing Excel dates store milliseconds without a timezone.
            expected = datetime.fromisoformat(card[key]).replace(tzinfo=None)
            assert abs((value - expected).total_seconds()) < 0.001
        else:
            assert ("" if value is None else str(value)) == card[key], (card["L4_ID"], key)
assert len(cards) == 622
assert sum(card["Evidence_URL"] in MAPPING.values() for card in cards) == 231
assert not any(card["Evidence_URL"] in MAPPING for card in cards)
manifest = json.loads((DATA / "manifest.json").read_text())
for item in manifest["files"].values():
    assert hashlib.sha256((DATA / item["path"]).read_bytes()).hexdigest() == item["sha256"]
source_hash = manifest["files"]["json"]["sha256"]
for name in ["semantic_space.json", "l3_semantic_colours.json", "l4_semantic_colours.json", "keyword_semantics.json"]:
    assert json.loads((DATA / name).read_text())["source_sha256"] == source_hash

# Optional local pre-edit backup gives stronger all-field and all-sheet checks.
backup = ROOT / "evidence_work/pdf_sync_before"
if (backup / "heart_l4_risk_cards.json").exists():
    original = json.loads((backup / "heart_l4_risk_cards.json").read_text())
    for before, after in zip(original, cards):
        expected = dict(before, Evidence_URL=MAPPING.get(before["Evidence_URL"], before["Evidence_URL"]))
        assert after == expected
    prior = openpyxl.load_workbook(backup / "HEART_L4_Risk_Cards.xlsx")
    assert prior.sheetnames == workbook.sheetnames
    for name in workbook.sheetnames:
        before, after = prior[name], workbook[name]
        assert (before.max_row, before.max_column) == (after.max_row, after.max_column)
        assert before.freeze_panes == after.freeze_panes
        assert before.sheet_view.showGridLines == after.sheet_view.showGridLines
        assert str(before.merged_cells) == str(after.merged_cells)
        for old_row, new_row in zip(before, after):
            for old, new in zip(old_row, new_row):
                expected = MAPPING.get(old.value, old.value) if name == "Risk Cards" and old.column == 22 else old.value
                assert new.value == expected, (name, old.coordinate)
                for style in ["font", "fill", "border", "alignment", "number_format", "protection"]:
                    assert copy(getattr(old, style)) == copy(getattr(new, style)), (name, old.coordinate, style)
    for name in ["semantic_space.json", "l3_semantic_colours.json", "l4_semantic_colours.json", "keyword_semantics.json"]:
        before = json.loads((backup / name).read_text())
        after = json.loads((DATA / name).read_text())
        before["source_sha256"] = source_hash
        if name == "l4_semantic_colours.json":
            before["l3_palette_sha256"] = hashlib.sha256((DATA / "l3_semantic_colours.json").read_bytes()).hexdigest()
        assert before == after
print("PASS: all 622 CSV/JSON/Excel cards match; 231 verified PDF URLs; manifest and graph hashes match; only requested values changed.")
