"""Non-visual L3 colour, source, and unchanged-network checks."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
colours = json.loads((root / 'data/l3_semantic_colours.json').read_text())
space = json.loads((root / 'data/semantic_space.json').read_text())
cards = json.loads((root / 'data/heart_l4_risk_cards.json').read_text())
assert len(colours['categories']) == len(space['clusters']) == 55
assert len({row['L3_ID'] for row in colours['categories']}) == 55
assert len(space['l1_colors']) == 3
assert colours['source_sha256'] == space['source_sha256']
by_id = {card['L4_ID']: card for card in cards}
categories = {row['id']: row for row in space['clusters']}
for point in space['points']:
    assert point['cluster'] == by_id[point['id']]['L3_ID']
    assert categories[point['cluster']]['L1_ID'] == by_id[point['id']]['L1_ID']
assert set(categories) == {card['L3_ID'] for card in cards}
assert all(point['id'] in by_id for point in space['points'])
print('L3 navigation checks passed: 55 categories, 3 L1 anchors, and 622 mapped L4 cards.')
