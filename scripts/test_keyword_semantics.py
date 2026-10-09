"""Non-visual, source-hash and numerical reproducibility smoke checks."""
import hashlib
import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'data/keyword_semantics.json').read_text())
definitions = json.loads((root / 'data/keyword_definitions.json').read_text())
cards = json.loads((root / 'data/heart_l4_risk_cards.json').read_text())
assert data['source_sha256'] == hashlib.sha256((root / 'data/heart_l4_risk_cards.json').read_bytes()).hexdigest()
assert data['definitions_sha256'] == hashlib.sha256((root / 'data/keyword_definitions.json').read_bytes()).hexdigest()
card_vectors = np.load(root / 'data/semantic_embeddings.npz', allow_pickle=False)
queries = np.load(root / 'data' / data['embedding_file'], allow_pickle=False)
assert str(queries['model_revision']) == str(card_vectors['model_revision']) == data['model_revision']
assert np.allclose(np.linalg.norm(queries['vectors'], axis=1), 1, atol=1e-5)
by_id = {card['L4_ID']: card for card in cards}
assert len(data['keywords']) == 17
for item in data['keywords']:
    assert item['definition'] and item['scope'] and item['reference_title'] and item['url'] and item['quote']
    assert len(item['quote'].split()) <= 20
    if item['mapping_mode'] == 'taxonomy':
        assert set(item['ids']) == {card['L4_ID'] for card in cards if card['L1_ID'] == item['l1']}
        continue
    assert item['url'].startswith('https://')
    assert len(item['scores']) == 622 and len({entry['id'] for entry in item['scores']}) == 622
    row = queries['ids'].tolist().index(item['id'])
    expected = queries['vectors'][row] @ card_vectors['vectors'].T
    score_by_id = dict(zip(card_vectors['ids'].tolist(), expected))
    assert all(abs(entry['cosine'] - float(score_by_id[entry['id']])) < 2e-6 for entry in item['scores'])
    expected_ids = {entry['id'] for entry in item['scores'] if entry['cosine'] >= item['threshold']}
    expected_ids.update(item['review_include'])
    expected_ids.difference_update(item['review_exclude'])
    assert set(item['ids']) == expected_ids
    assert item['mapping_review']['rationale']
    assert all(entry['reason'] for action in ('include', 'exclude') for entry in item['mapping_review'][action])
    reviewed = {entry['id'] for action in ('include', 'exclude') for entry in item['mapping_review'][action]}
    assert {entry['id'] for entry in item['scores'] if entry['cosine'] >= item['threshold']}.issubset(reviewed)
space = json.loads((root / 'data/semantic_space.json').read_text())
assert space['keywords'] == data['keywords']
print('Keyword smoke checks passed: 17 definitions, 14 semantic queries, 3 exact domain filters; scores and membership reproduced.')
