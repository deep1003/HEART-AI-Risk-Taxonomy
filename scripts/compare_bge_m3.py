"""Local, resumable embedding comparison. Never alters canonical website data."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence_work/bge_m3_comparison_20261009'
API = 'http://127.0.0.1:11434/api/'


def request(endpoint, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + endpoint, data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)


def neighbours(vectors):
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -1)
    order = np.argsort(-similarities, axis=1, kind='stable')[:, :8]
    return similarities, order


def partition(similarities, order, threshold):
    graph = nx.Graph()
    graph.add_nodes_from(range(len(order)))
    for i, candidates in enumerate(order):
        for j in candidates:
            if similarities[i, j] >= threshold:
                graph.add_edge(i, int(j), weight=float(similarities[i, j]))
    groups = nx.community.louvain_communities(graph, weight='weight', seed=23)
    labels = np.zeros(len(order), dtype=int)
    for label, members in enumerate(groups):
        for i in members:
            labels[i] = label
    return graph, groups, labels


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = (ROOT / 'data/heart_l4_risk_cards.json').read_bytes()
    cards = sorted(json.loads(raw), key=lambda c: c['L4_ID'])
    ids = [c['L4_ID'] for c in cards]
    texts = [f"{c['L4_Name_en']}. {c['Risk_Definition_en']}" for c in cards]
    text_hash = hashlib.sha256(json.dumps(texts).encode()).hexdigest()
    model = next(m for m in request('tags')['models'] if m['name'] == 'bge-m3:latest')
    provenance = {'model': model, 'ollama': request('version'),
                  'source_sha256': hashlib.sha256(raw).hexdigest(), 'text_sha256': text_hash,
                  'input': 'English L4 name plus definition; same as MiniLM',
                  'truncate': False, 'normalisation': 'L2', 'networkx': nx.__version__}
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    checkpoint = OUT / 'checkpoint.json'
    saved = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    if saved:
        assert saved['text_sha256'] == text_hash and saved['digest'] == model['digest']
    vectors = saved.get('vectors', [])
    started = time.monotonic()
    for start in range(len(vectors), len(texts), 8):
        result = request('embed', {'model': 'bge-m3:latest', 'input': texts[start:start+8],
                                   'truncate': False, 'keep_alive': '5m'})
        batch = result['embeddings']
        assert len(batch) == len(texts[start:start+8])
        assert all(len(v) == 1024 for v in batch)
        vectors.extend(batch)
        checkpoint.write_text(json.dumps({'text_sha256': text_hash, 'digest': model['digest'],
                                          'vectors': vectors}))
        print(f'Embedded {len(vectors)}/{len(texts)}', flush=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    assert vectors.shape == (622, 1024) and np.isfinite(vectors).all()
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    assert (norms > 0).all()
    vectors /= norms
    np.savez_compressed(OUT / 'bge_m3_embeddings.npz', vectors=vectors, ids=np.array(ids),
                        text_sha256=text_hash, model_digest=model['digest'])
    baseline_path = ROOT / 'evidence_work/minilm_baseline_20261009/semantic_embeddings.npz'
    baseline = np.load(baseline_path if baseline_path.exists() else ROOT / 'data/semantic_embeddings.npz', allow_pickle=False)
    assert baseline['vectors'].shape[1] == 384
    assert baseline['ids'].tolist() == ids and str(baseline['text_sha256']) == text_hash
    old = baseline['vectors']
    old_sim, old_order = neighbours(old)
    new_sim, new_order = neighbours(vectors)
    old_graph, old_groups, old_labels = partition(old_sim, old_order, .45)
    l3 = [c['L3_ID'] for c in cards]
    def same_l3(order):
        return float(np.mean([l3[i] == l3[j] for i, row in enumerate(order) for j in row]))
    comparisons = []
    for threshold in [.45, .5, .55, .6, .65, .7, .75]:
        graph, groups, labels = partition(new_sim, new_order, threshold)
        comparisons.append({'threshold': threshold, 'edges': graph.number_of_edges(),
                            'communities': len(groups), 'isolates': len(list(nx.isolates(graph))),
                            'components': nx.number_connected_components(graph),
                            'ARI_vs_MiniLM_partition': adjusted_rand_score(old_labels, labels)})
    summary = {'cards': len(cards), 'dimensions': 1024, 'runtime_seconds_this_run': time.monotonic()-started,
               'mean_top8_neighbour_overlap': float(np.mean([len(set(a)&set(b))/8 for a,b in zip(old_order,new_order)])),
               'same_L3_top8_MiniLM': same_l3(old_order), 'same_L3_top8_BGE_M3': same_l3(new_order),
               'MiniLM_edges': old_graph.number_of_edges(), 'MiniLM_communities': len(old_groups),
               'BGE_M3_top8_cosine_quantiles': np.quantile(new_sim[np.arange(622)[:,None],new_order], [0,.1,.5,.9,1]).tolist(),
               'threshold_sensitivity': comparisons,
               'limitations': 'Same-L3 neighbour agreement is a diagnostic, not gold semantic accuracy. No expert pair labels or statistical accuracy claim. No taxonomy assignments changed.'}
    (OUT / 'comparison.json').write_text(json.dumps(summary, indent=2))
    rows = [{'id': ids[i], 'name': cards[i]['L4_Name_en'], 'L3': l3[i],
             'MiniLM_top8': [ids[j] for j in old_order[i]],
             'BGE_M3_top8': [ids[j] for j in new_order[i]]} for i in range(622)]
    (OUT / 'neighbour_review.json').write_text(json.dumps(rows, indent=2))
    assert hashlib.sha256((ROOT / 'data/heart_l4_risk_cards.json').read_bytes()).hexdigest() == provenance['source_sha256']
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
