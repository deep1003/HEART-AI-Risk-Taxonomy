"""Non-visual L3 colour, source, and unchanged-network checks."""
import json
import subprocess
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
colours = json.loads((root / 'data/l3_semantic_colours.json').read_text())
space = json.loads((root / 'data/semantic_space.json').read_text())
cards = json.loads((root / 'data/heart_l4_risk_cards.json').read_text())
assert len(colours['categories']) == len(space['clusters']) == 47
assert len({row['color'] for row in colours['categories']}) == 47
assert len(space['l1_colors']) == 3
assert colours['source_sha256'] == space['source_sha256']
cache = np.load(root / 'data' / colours['embedding_file'], allow_pickle=False)
assert cache['vectors'].shape == (47,1024)
assert np.allclose(np.linalg.norm(cache['vectors'],axis=1),1,atol=1e-5)
assert str(cache['model_revision']) == colours['model_revision']
by_id = {card['L4_ID']: card for card in cards}
categories = {row['id']: row for row in space['clusters']}
for point in space['points']:
    assert point['cluster'] == by_id[point['id']]['L3_ID']
    assert categories[point['cluster']]['L1_ID'] == by_id[point['id']]['L1_ID']
for category in colours['categories']:
    assert 0 <= category['boundary_blend'] <= .35
    assert 0 <= category['neighbour_mix_weight'] <= .45
    assert category['neighbour_l3'] != category['L3_ID']
old = json.loads(subprocess.check_output(['git','show','4af0e22:data/semantic_space.json'],cwd=root))
assert old['edges'] == space['edges']
assert old['clusters'] == space['graph_communities']
for previous, current in zip(old['points'],space['points']):
    assert all(previous[key] == current[key] for key in ('id','x','y','degree','strength'))
    assert previous['cluster'] == current['graph_community']
assert old['keywords'] == space['keywords'] and old['scenarios'] == space['scenarios']
print('L3 colour checks passed: 47 categories, 3 L1 anchors, unchanged L4 coordinates/links/assignments and keyword/scenario membership.')
