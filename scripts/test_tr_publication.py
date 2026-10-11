"""Validate the reference-reviewed publication and preserved prior releases."""
import hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
about=(ROOT/"about.html").read_text()
meta=json.loads((ROOT/"reports/release_20261011_reference_review.json").read_text())
for name,item in meta["files"].items():
 data=(ROOT/"reports"/name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==item["sha256"]
 assert len(data)==item["bytes"]
 assert "reports/"+name in about
with zipfile.ZipFile(ROOT/"reports/HEART_Technical_Report_20261011_reference_review_source.zip") as z:
 names=[n for n in z.namelist() if not n.endswith("/")]
 assert len(names)==57
 prefix="overleaf_rai_risk_taxonomy_current/"
 for line in z.read(prefix+"checksums.sha256").decode().splitlines():
  expected,name=line.split("  ",1)
  assert hashlib.sha256(z.read(prefix+name)).hexdigest()==expected
 assert z.read(prefix+"RAI_Risk_Taxonomy_Technical_Report.pdf")==(ROOT/"reports/HEART_Technical_Report_20261011_reference_review.pdf").read_bytes()
 evaluation=z.read(prefix+"sections/05a_algorithm_evaluation.tex").decode()
 for marker in ["432/622","390/622","69.45","62.70","817","875","83.12"]:
  assert marker in evaluation and marker in about,marker
for release in meta["previous_releases_preserved"]:
 for name,item in json.loads((ROOT/"reports"/release).read_text())["files"].items():
  assert hashlib.sha256((ROOT/"reports"/name).read_bytes()).hexdigest()==item["sha256"]
for disclosure in ["evaluation-details","mapping-details"]:
 opening=re.search(r'<details id="'+disclosure+r'"[^>]*>',about).group()
 assert not re.search(r"\bopen\b",opening)
for marker in ["Reference verification.","Historical reproducibility.","not paid normative clauses","not semantic accuracy","not fully independent semantic validation"]:
 assert marker in about,marker
cards=json.loads((ROOT/"data/heart_l4_risk_cards.json").read_text())
assert len(cards)==622 and len({c["L3_ID"] for c in cards})==47
assert meta["pdf_pages"]==37 and meta["reference"]["unchanged"]
assert sum(meta["reference_review"][k] for k in ["relevant_original_text","partial_text","official_ISO_scope_only"])==49
print("PASS: 37 pages, 57 sources, checksums, unchanged results/reference, bounded citations and preserved prior downloads.")
