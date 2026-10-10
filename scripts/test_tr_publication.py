"""Validate public TR provenance, numerical summaries and collapsed disclosures."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
about = (ROOT/'about.html').read_text()
metadata = json.loads((ROOT/'reports/release_20261010.json').read_text())
for name, expected in metadata['files'].items():
    data = (ROOT/'reports'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256']
    assert len(data) == expected['bytes']
    assert f'reports/{name}' in about
source = ROOT/'reports/HEART_Technical_Report_20261010_source.zip'
with zipfile.ZipFile(source) as archive:
    names = [name for name in archive.namelist() if not name.endswith('/')]
    assert len(names) == 57
    assert 'Technical Report, 10 October 2026' in archive.read('main.tex').decode()
    evaluation = archive.read('overleaf_rai_risk_taxonomy_current/sections/05a_algorithm_evaluation.tex').decode()
    for marker in ['432/622', '390/622', '69.45', '62.70', '817', '875', '0.2527', '517/622', '83.12']:
        assert marker in evaluation and marker in about
    assert round(432/622*100, 2) == 69.45
    assert round(390/622*100, 2) == 62.70
    assert round(517/622*100, 2) == 83.12
    assert 'appendix_c_mit.tex' in ' '.join(names)
    prefix = 'overleaf_rai_risk_taxonomy_current/'
    for line in archive.read(prefix+'checksums.sha256').decode().splitlines():
        expected, name = line.split('  ', 1)
        assert hashlib.sha256(archive.read(prefix+name)).hexdigest() == expected
for disclosure in ['evaluation-details', 'mapping-details']:
    opening = re.search(r'<details id="'+disclosure+r'"[^>]*>', about).group()
    assert not re.search(r'\bopen\b', opening)
for caveat in ['not semantic accuracy', 'not fully independent semantic validation',
               'not a uniquely correct taxonomy', 'not independent objective accuracy']:
    assert caveat in about
cards = json.loads((ROOT/'data/heart_l4_risk_cards.json').read_text())
assert len(cards) == 622
assert len({card['L3_ID'] for card in cards}) == 47
assert metadata['reference']['unchanged']
print('TR publication checks passed: 57 source files, checksums, numerical agreement, caveats and collapsed details.')
