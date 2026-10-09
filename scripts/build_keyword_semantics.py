"""Build source-defined exploratory keyword retrieval without changing taxonomy."""
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def api(endpoint, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request('http://127.0.0.1:11434/api/' + endpoint,
                                    data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def main():
    source = ROOT / 'data/heart_l4_risk_cards.json'
    raw = source.read_bytes()
    cards = sorted(json.loads(raw), key=lambda card: card['L4_ID'])
    definitions_raw = (ROOT / 'data/keyword_definitions.json').read_bytes()
    definitions = json.loads(definitions_raw)
    cache = np.load(ROOT / 'data/semantic_embeddings.npz', allow_pickle=False)
    assert cache['ids'].tolist() == [card['L4_ID'] for card in cards]
    texts = [f"{card['L4_Name_en']}. {card['Risk_Definition_en']}" for card in cards]
    assert str(cache['text_sha256']) == hashlib.sha256(json.dumps(texts).encode()).hexdigest()
    concepts = [item for item in definitions if item['mapping_mode'] == 'semantic']
    queries = [f"{item['name']}. {item['definition']}" for item in concepts]
    query_hash = hashlib.sha256(json.dumps(queries).encode()).hexdigest()
    checkpoint = ROOT / f'data/keyword_embeddings_{query_hash[:12]}.npz'
    if checkpoint.exists():
        saved = np.load(checkpoint, allow_pickle=False)
        assert str(saved['model_revision']) == str(cache['model_revision'])
        assert str(saved['query_sha256']) == query_hash, 'Definitions changed; explicitly rebuild the keyword cache.'
        vectors = saved['vectors']
    else:
        model = next(model for model in api('tags')['models'] if model['name'] == 'bge-m3:latest')
        assert model['digest'] == str(cache['model_revision'])
        vectors = []
        for start in range(0, len(queries), 4):
            vectors.extend(api('embed', {'model': 'bge-m3:latest', 'input': queries[start:start+4],
                                        'truncate': False, 'keep_alive': '5m'})['embeddings'])
        vectors = np.asarray(vectors, dtype=np.float32)
        assert vectors.shape == (len(concepts), 1024) and np.isfinite(vectors).all()
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        np.savez_compressed(checkpoint, vectors=vectors, ids=np.array([item['id'] for item in concepts]),
                            query_sha256=query_hash, model_revision=str(cache['model_revision']))
    similarities = vectors @ cache['vectors'].T
    by_concept = {item['id']: index for index, item in enumerate(concepts)}
    keywords = []
    for item in definitions:
        result = dict(item)
        if item['mapping_mode'] == 'taxonomy':
            result['ids'] = [card['L4_ID'] for card in cards if card['L1_ID'] == item['l1']]
            result['scores'] = []
        else:
            scores = similarities[by_concept[item['id']]]
            threshold = item['threshold']
            included = set(item.get('review_include', []))
            excluded = set(item.get('review_exclude', []))
            assert included.isdisjoint(excluded)
            result['scores'] = [{'id': cards[index]['L4_ID'], 'cosine': round(float(scores[index]), 6)}
                                for index in np.argsort(-scores, kind='stable')]
            result['ids'] = [entry['id'] for entry in result['scores']
                             if entry['id'] not in excluded and
                             (entry['cosine'] >= threshold or entry['id'] in included)]
        assert set(result['ids']).issubset(set(cache['ids'].tolist()))
        keywords.append(result)
    result = {'source_sha256': hashlib.sha256(raw).hexdigest(),
              'definitions_sha256': hashlib.sha256(definitions_raw).hexdigest(),
              'model_revision': str(cache['model_revision']), 'dimensions': 1024,
              'query_sha256': query_hash, 'keywords': keywords,
              'embedding_file': checkpoint.name,
              'limitations': 'Source-grounded semantic retrieval, not validated classification accuracy. '
                              'Cosine thresholds and documented expert scope corrections are exploratory. '
                              'L1 domain filters use existing human-approved taxonomy assignments. No EM or remapping.'}
    (ROOT / 'data/keyword_semantics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    assert source.read_bytes() == raw
    print(json.dumps({item['name']: len(item['ids']) for item in keywords}, indent=2))


if __name__ == '__main__':
    main()
