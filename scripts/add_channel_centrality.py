"""Add exact normalized centrality to the frozen full channel networks."""
import csv
import json
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'data/incidents/channels'
path = folder / 'networks.json'
data = json.loads(path.read_text())
metrics = {}
for channel, source in data['channels'].items():
    graph = nx.Graph()
    graph.add_nodes_from(node['id'] for node in source['nodes'])
    graph.add_edges_from((edge['source'], edge['target']) for edge in source['edges'])
    degree = nx.degree_centrality(graph)
    between = nx.betweenness_centrality(graph, normalized=True, weight=None, endpoints=False)
    for node in source['nodes']:
        assert graph.degree(node['id']) == node['degree']
        node['degree_centrality'] = degree[node['id']]
        node['betweenness_centrality'] = between[node['id']]
        assert 0 <= degree[node['id']] <= 1 and 0 <= between[node['id']] <= 1
        metrics[channel, node['id']] = node
    print(channel, len(graph), metrics[channel, 'P_SYS_CONTROL_003']['degree_centrality'], metrics[channel, 'P_SYS_CONTROL_003']['betweenness_centrality'])
data['centrality_definition'] = {'network': 'Full undirected unweighted channel network, including all activated cards', 'degree_centrality': 'Distinct neighbors / (activated cards - 1)', 'betweenness_centrality': 'Exact shortest-path betweenness, normalized by 2 / ((n - 1) * (n - 2)); endpoints excluded; disconnected pairs contribute zero'}
path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
path = folder / 'nodes.csv'
with path.open(newline='') as stream:
    reader = csv.DictReader(stream)
    rows = list(reader)
    fields = list(reader.fieldnames)
for field in ['degree_centrality', 'betweenness_centrality']:
    if field not in fields:
        fields.append(field)
for row in rows:
    node = metrics[row['channel'], row['id']]
    for field in ['degree_centrality', 'betweenness_centrality']:
        row[field] = node[field]
with path.open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
