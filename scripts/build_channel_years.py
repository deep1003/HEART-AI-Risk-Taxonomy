"""Build annual views from the frozen record-to-card index, without remapping."""
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import networkx as nx
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'data/incidents/channels'
base=json.loads((folder/'networks.json').read_text())
result={}
for ch,c in base['channels'].items():
    source=json.loads((folder/f'incidents-{ch}.json').read_text())
    records=source['records'];cards={n['id']:n for n in c['nodes']};by_record=defaultdict(list)
    for card,indices in source['by_card'].items():
        for i in indices:by_record[i].append(card)
    years=defaultdict(list)
    for i,r in enumerate(records):
        assert len(set(by_record[i]))==3
        years[int(r['date'][:4])].append(i)
    assert sum(map(len,years.values()))==c['n']
    output={}
    for year,indices in sorted(years.items()):
        counts=Counter();pairs=Counter();cross=0
        for i in indices:
            ids=sorted(set(by_record[i]));counts.update(ids);pairs.update(combinations(ids,2));cross+=len({cards[k]['domain'] for k in ids})>1
        assert sum(counts.values())==3*len(indices)
        assert sum(pairs.values())==3*len(indices)
        g=nx.Graph();g.add_nodes_from(sorted(counts));g.add_edges_from(pairs)
        dc=nx.degree_centrality(g);bc=nx.betweenness_centrality(g,normalized=True,weight=None)
        nodes=[]
        for id in g:
            node={**cards[id],'activations':counts[id],'degree':g.degree(id),'degree_centrality':dc[id],'betweenness_centrality':bc[id]}
            node['degree_rank']=1+sum(g.degree(j)>g.degree(id) for j in g)
            node['betweenness_rank']=1+sum(round(bc[j],12)>round(bc[id],12) for j in g)
            nodes.append(node)
        candidates=set()
        for domain in ['L1_G','L1_A','L1_P']:
            candidates.update(sorted((id for id in g if cards[id]['domain']==domain),key=lambda id:(-counts[id],id))[:25])
        shown=sorted((p for p in pairs if set(p)<=candidates),key=lambda p:(-pairs[p],p))[:240]
        edges=[{'source':a,'target':b,'count':v,'per_1000':v/len(indices)*1000} for (a,b),v in sorted(pairs.items())]
        output[str(year)]={'n':len(indices),'nodes':nodes,'edges':edges,'node_count':len(g),'edge_count':len(pairs),'cross_rate':cross/len(indices),'overview':{'ids':sorted({k for p in shown for k in p}),'edges':shown}}
    result[ch]={'years':output,'min_year':min(years),'max_year':max(years)}
    print(ch,len(years),sum(v['n'] for v in output.values()))
(folder/'years.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
