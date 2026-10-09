#!/usr/bin/env python3
"""Recompute the read-only HEART semantic graph from the current card text."""
import hashlib
import json
from importlib.metadata import version
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from build_semantic_space import SCENARIOS, TOPICS, match

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'BAAI/bge-m3 (Ollama bge-m3:latest)'
THRESHOLD = .60
SEED = 23


def main():
    source = ROOT / 'data/heart_l4_risk_cards.json'
    raw = source.read_bytes()
    cards = sorted(json.loads(raw), key=lambda card: card['L4_ID'])
    texts = [f"{card['L4_Name_en']}. {card['Risk_Definition_en']}" for card in cards]
    text_hash = hashlib.sha256(json.dumps(texts).encode()).hexdigest()
    experiment = ROOT / 'evidence_work/bge_m3_comparison_20261009'
    if (experiment / 'provenance.json').exists():
        provenance = json.loads((experiment / 'provenance.json').read_text())
        revision = provenance['model']['digest']
        ollama_version = provenance['ollama']['version']
        cached = np.load(experiment / 'bge_m3_embeddings.npz', allow_pickle=False)
        assert str(cached['model_digest']) == revision
    else:
        published = json.loads((ROOT / 'data/semantic_space.json').read_text())['method']
        assert published['embedding_model'] == MODEL
        revision, ollama_version = published['model_revision'], published['ollama_version']
        cached = np.load(ROOT / 'data/semantic_embeddings.npz', allow_pickle=False)
        assert str(cached['model_revision']) == revision
    assert str(cached['text_sha256']) == text_hash
    assert cached['ids'].tolist() == [card['L4_ID'] for card in cards]
    vectors = cached['vectors']
    assert vectors.shape == (622, 1024) and np.isfinite(vectors).all()
    vectors_path = ROOT / 'data/semantic_embeddings.npz'
    np.savez_compressed(vectors_path, vectors=vectors, ids=cached['ids'],
                        text_sha256=text_hash, model_revision=revision)
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -1)
    graph = nx.Graph()
    graph.add_nodes_from(range(len(cards)))
    for index in range(len(cards)):
        for other in np.argsort(-similarities[index], kind='stable')[:8]:
            weight = float(similarities[index, other])
            if weight >= THRESHOLD:
                graph.add_edge(index, int(other), weight=weight)
    groups = nx.community.louvain_communities(graph, weight='weight', resolution=1.0, seed=SEED)
    groups = sorted(groups, key=lambda group: (-len(group), min(group)))
    membership = {node: group for group, members in enumerate(groups) for node in members}
    initial = nx.spring_layout(graph, iterations=100, seed=SEED, weight='weight')
    # NetworkX evaluates the self-distance 0/0 before zeroing its diagonal.
    # Suppress only that arithmetic warning, then reject any nonfinite layout.
    with np.errstate(invalid='ignore', divide='ignore'):
        positions = nx.forceatlas2_layout(graph, pos=initial, max_iter=350, scaling_ratio=8,
                                         gravity=.15, weight='weight', linlog=True, seed=SEED)
    xy = np.array([positions[i] for i in range(len(cards))])
    xy -= (xy.max(axis=0) + xy.min(axis=0)) / 2
    xy /= max(float(np.abs(xy).max()), 1e-12)
    palette = ['#6850cf','#17a88d','#d94e76','#359ac6','#b58a22','#bf55c2',
               '#6a9b28','#dd773b','#3e6fc7','#a85f68','#3b9ba3','#855bbe',
               '#7f8b2c','#cf5870','#49825a','#ab6f39']
    short_names = {
        'Evaluation and Assurance Failure':'Evaluation & assurance',
        'Out-of-Domain Performance Degradation':'Performance',
        'Other Unlawful Activity':'Unlawful activity',
        'Unsafe Physical Control and Actuation':'Physical control',
        'Human-Robot Physical Safety Failure':'Physical safety',
        'Representational Harm and Stereotyping':'Representation',
        'Allocative Discrimination':'Discrimination',
        'Privacy Violation':'Privacy', 'Copyright Infringement':'Copyright',
        'Goal Misalignment':'Goal misalignment',
        'Excessive Authority and Agency':'Authority',
        'Governance and Accountability Void':'Governance',
        'Inequality and Power Concentration':'Inequality',
        'Erosion of Democracy and Civic Order':'Democracy',
        'Political Bias and Manipulation':'Political manipulation',
        'Security and Adversarial Robustness Failure':'Cybersecurity',
        'Unethical Conduct and Manipulation':'Manipulation',
        'Unhealthy Human-AI Relationship':'Human-AI relationships',
    }
    clusters = []
    for group, members in enumerate(groups):
        families = Counter(cards[i]['L3_Name_en'] for i in sorted(members))
        dominant = families.most_common(2)
        name = dominant[0][0]
        if len(dominant) > 1 and dominant[0][1] / len(members) < .55:
            name += ' / ' + dominant[1][0]
        centroid = xy[sorted(members)].mean(axis=0)
        label = ' / '.join(short_names.get(term,term) for term,count in dominant[:2 if len(dominant)>1 and dominant[0][1]/len(members)<.55 else 1])
        clusters.append({'id':f'community-{group}', 'name':name, 'label':label, 'color':palette[group % len(palette)],
                         'x':round(float(centroid[0]),7), 'y':round(float(centroid[1]),7),
                         'ids':[cards[i]['L4_ID'] for i in sorted(members)],
                         'dominant_l3': [{'name':name, 'count':count} for name,count in dominant]})
    degrees = dict(graph.degree())
    strengths = dict.fromkeys(graph.nodes(), 0.0)
    for a,b,attrs in graph.edges(data=True):
        weight = round(attrs['weight'],6)
        strengths[a] += weight
        strengths[b] += weight
    result = {'schema_version':'2.0', 'card_count':len(cards), 'source_file':source.name,
              'source_sha256':hashlib.sha256(raw).hexdigest(),
              'method': {'embedding_model':MODEL, 'model_revision':revision, 'embedding_dimensions':1024,
                         'features':'English L4 name and definition; Ollama dense embeddings, no truncation, L2 normalised',
                         'projection':'Weighted ForceAtlas2 network layout, no clipping of outlying nodes',
                         'clustering':'Weighted Louvain graph communities, resolution 1.0, seed 23',
                         'networkx_version':nx.__version__,
                         'ollama_version':ollama_version,
                         'community_function':'networkx.algorithms.community.louvain_communities',
                         'edge_rule':'Union of each card’s eight closest cosine neighbours, cosine >= 0.60; no artificial links',
                         'cosine_threshold':THRESHOLD,
                         'node_size':'Weighted degree (strength): sum of published incident cosine weights; area linearly scaled over the full-network min/max to radii 3 to 15 display pixels. Fixed across filters, not severity or probability.',
                         'scenario_membership':'Editorial overlapping conditional applicability lenses',
                         'random_seed':SEED, 'edge_count':graph.number_of_edges(),
                         'isolated_nodes':len(list(nx.isolates(graph))),
                         'connected_components':nx.number_connected_components(graph),
                         'modularity':round(nx.community.modularity(graph,groups,weight='weight'),6),
                         'text_sha256':text_hash, 'embedding_sha256':hashlib.sha256(vectors_path.read_bytes()).hexdigest(),
                         'limitations':'Exploratory semantic proximity only, not causal propagation or validated deployment applicability. Graph communities are not reassigned L3 categories. No EM is run.'},
              'points':[{'id':card['L4_ID'], 'x':round(float(xy[i,0]),7), 'y':round(float(xy[i,1]),7),
                         'cluster':f'community-{membership[i]}', 'degree':degrees[i], 'strength':round(strengths[i],6)} for i,card in enumerate(cards)],
              'edges':[[cards[a]['L4_ID'],cards[b]['L4_ID'],round(attrs['weight'],6)]
                       for a,b,attrs in sorted(graph.edges(data=True))],
              'clusters':clusters,
              'scenarios':[{k:rule[k] for k in ('id','name','name_ko','description')} |
                           {'ids':[card['L4_ID'] for card in cards if match(card,rule) and card['L4_ID'] not in rule.get('exclude',[])]}
                           for rule in SCENARIOS],
              'keywords':[{'id':rule['id'],'name':rule['name'],'ids':[card['L4_ID'] for card in cards if match(card,rule)]} for rule in TOPICS]}
    assert np.isfinite(xy).all() and len(cards)==622
    assert source.read_bytes()==raw
    (ROOT/'data/semantic_space.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cards':len(cards),'communities':len(groups),**result['method']},indent=2))


if __name__ == '__main__':
    main()
