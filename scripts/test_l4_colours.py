"""Non-visual solid-colour and unchanged-network smoke checks."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
data = json.loads((root/'data/l4_semantic_colours.json').read_text())
space = json.loads((root/'data/semantic_space.json').read_text())
assert data['source_sha256'] == space['source_sha256']
assert data['l3_palette_sha256'] == hashlib.sha256((root/'data/l3_semantic_colours.json').read_bytes()).hexdigest()
assert len(data['points']) == 622 and len({p['id'] for p in data['points']}) == 622
by_id = {point['id']:point for point in data['points']}
for point in space['points']:
    colour = by_id[point['id']]
    assert point['color'] == colour['color']
    assert point['cluster'] == colour['l3']
    assert 0 <= colour['neighbour_mix_weight'] <= .30
    assert colour['neighbour_l3'] != colour['l3']
old = json.loads(subprocess.check_output(['git','show','120bb26:data/semantic_space.json'],cwd=root))
assert old['edges'] == space['edges'] and old['clusters'] == space['clusters']
assert old['keywords'] == space['keywords'] and old['scenarios'] == space['scenarios']
for before, after in zip(old['points'],space['points']):
    assert all(before[key] == after[key] for key in before)
assert len({point['color'] for point in data['points']}) > 500
print('Solid L4 colour smoke checks passed: 622 nodes; coordinates, links, sizes, L3 assignments and filters unchanged.')
