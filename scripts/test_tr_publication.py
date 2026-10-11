"""Validate public TR provenance, numerical summaries and collapsed disclosures."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
about = (ROOT/'about.html').read_text()
metadata = json.loads((ROOT/'reports/release_20261011.json').read_text())
for name, expected in metadata['files'].items():
    data = (ROOT/'reports'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256']
    assert len(data) == expected['bytes']
    assert f'reports/{name}' in about
source = ROOT/'reports/HEART_Technical_Report_20261011_source.zip'
with zipfile.ZipFile(source) as archive:
    names = [name for name in archive.namelist() if not name.endswith('/')]
    assert len(names) == 57
    assert 'Technical Report, 11 October 2026' in archive.read('main.tex').decode()
    evaluation = archive.read('overleaf_rai_risk_taxonomy_current/sections/05a_algorithm_evaluation.tex').decode()
    for marker in ['432/622', '390/622', '69.45', '62.70', '817', '875', '0.2527', '517/622', '83.12']:
        assert marker in evaluation and marker in about
    assert round(432/622*100, 2) == 69.45
    assert round(390/622*100, 2) == 62.70
    assert round(517/622*100, 2) == 83.12
    assert 'appendix_c_mit.tex' in ' '.join(names)
    for marker in ['78d29c0cbe8d', 'all 28 archived pass fractions',
                   'not command-log-confirmed process boundaries',
                   'not established causes', '1.65572', 'prior replay validator']:
        assert marker in evaluation
    prefix = 'overleaf_rai_risk_taxonomy_current/'
    for line in archive.read(prefix+'checksums.sha256').decode().splitlines():
        expected, name = line.split('  ', 1)
        assert hashlib.sha256(archive.read(prefix+name)).hexdigest() == expected
    assert archive.read(prefix+'RAI_Risk_Taxonomy_Technical_Report.pdf') == (ROOT/'reports/HEART_Technical_Report_20261011.pdf').read_bytes()
for marker in ['Confirmed text and cache provenance', 'Confirmed reset mechanism; inferred restart intervals',
               'all 406 contiguous restart segments', 'not verified process logs',
               'F1–F2, F3–F5, F6–F9, F10–F13, F14–F19, F20–F27 and F28',
               'all 28 archived null pass fractions', 'F5/F8/F11/F13/F15/F19',
               '1.65572', 'hypotheses, not established causes',
               'no embeddings were regenerated', 'not the recovered cache-key wording',
               'does not widen the original replay validator', '11 October 2026, 43 pages']:
    assert marker in about, marker
assert metadata['audit']['inferred_restart_intervals'] == [[1,2],[3,5],[6,9],[10,13],[14,19],[20,27],[28,28]]
assert not metadata['audit']['exact_historical_execution_certified']
assert not metadata['audit']['embeddings_regenerated']
assert metadata['audit']['archived_pass_fractions_reproduced'] == 28
assert metadata['pdf_pages'] == 43
previous = json.loads((ROOT/'reports/release_20261010.json').read_text())
for name, expected in previous['files'].items():
    assert hashlib.sha256((ROOT/'reports'/name).read_bytes()).hexdigest() == expected['sha256']
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
print('TR publication checks passed: new 43-page master, 57 sources, checksums, audit distinctions, unchanged prior release, scores and collapsed details.')
