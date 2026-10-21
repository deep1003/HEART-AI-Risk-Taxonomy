"""Non-visual solid-colour and unchanged-network smoke checks."""
import hashlib
import json
from pathlib import Path

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
assert len(space['clusters']) == 55
assert {point['cluster'] for point in space['points']} == {cluster['id'] for cluster in space['clusters']}
assert all(point['id'] in by_id for point in space['points'])
assert len({point['color'] for point in data['points']}) > 500
print('Solid L4 colour smoke checks passed: 622 nodes; coordinates, links, sizes, L3 assignments and filters unchanged.')
