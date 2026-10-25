#!/usr/bin/env python3
"""Build aggregate public networks from the paper's frozen channel mappings.

Usage: python scripts/build_channel_incidents.py --inputs PATH
Only analytic records, frozen candidate assignments, and published inventory metadata
are read. No incident narratives, identities, or adjudication fields are exported.
"""
import argparse
from collections import Counter
from itertools import combinations
import csv
import hashlib
import json
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261021
BRIDGE = 'A_INT_OVERSIGHT_003'
DOMAINS = {'L1_G': 'General AI', 'L1_A': 'Agentic AI', 'L1_P': 'Physical AI'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def shared_layout(graph, radii):
    """Deterministic joint layout and collision separation in SVG coordinates."""
    ids = sorted(graph)
    g = nx.Graph()
    g.add_nodes_from(ids)
    g.add_edges_from(sorted(graph.edges()))
    for u,v in g.edges:
        g[u][v]['weight'] = graph[u][v]['weight'] ** .35
    raw = nx.spring_layout(g, seed=SEED, weight='weight', iterations=500, k=2.3 / np.sqrt(len(g)))
    pts = np.array([raw[i] for i in ids])
    pts = (pts-pts.min(0)) / np.maximum(pts.max(0)-pts.min(0),1e-9)
    pts = pts * np.array([1040,550]) + np.array([80,65])
    rng = np.random.default_rng(SEED)
    for _ in range(180):
        moved=False
        for i in range(len(ids)):
            delta=pts[i+1:]-pts[i]
            dist=np.linalg.norm(delta,axis=1)
            minimum=np.array([radii[ids[i]]+radii[j]+(22 if len(ids)<=120 else 10) for j in ids[i+1:]])
            for z in np.flatnonzero(dist<minimum):
                j=i+1+z
                direction=delta[z]/dist[z] if dist[z]>1e-9 else rng.normal(size=2)
                direction=direction/max(np.linalg.norm(direction),1e-9)
                shift=direction*(minimum[z]-dist[z])*.51
                pts[i]-=shift;pts[j]+=shift;moved=True
        pts=np.clip(pts,[35,35],[1165,645])
        if not moved:break
    return {i:[round(float(x),3) for x in p] for i,p in zip(ids,pts)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,required=True)
    args=parser.parse_args()
    recpath=args.inputs/'channel_analytic_records.csv.gz'
    edgepath=args.inputs/'channel_edges_k5.csv.gz'
    records=pd.read_csv(recpath)
    edges=pd.read_csv(edgepath)
    inventory=json.loads((ROOT/'data/heart_l4_risk_cards.json').read_text())
    cards={c['L4_ID']:c for c in inventory}
    semantic=json.loads((ROOT/'data/semantic_space.json').read_text())
    color={p['id']:p['color'] for p in semantic['points']}
    assert len(cards)==622
    assert len({c['L3_ID'] for c in inventory})==55
    assert Counter(c['L1_ID'] for c in inventory)=={'L1_G':491,'L1_A':68,'L1_P':63}
    assert records.canonical_incident_id.is_unique
    assert len(records)==12200
    assert records.channel.value_counts().to_dict()=={'AIM':10449,'AIID':1751}
    top=edges[edges['rank']<=3].copy()
    assert top.groupby('canonical_incident_id').size().eq(3).all()
    assert not top.duplicated(['canonical_incident_id','L4_ID']).any()
    assert set(top.L4_ID)<=set(cards)
    for _,row in top.drop_duplicates('L4_ID').iterrows():
        assert cards[row.L4_ID]['L1_ID']==row.L1_ID
        assert cards[row.L4_ID]['L4_Name_en']==row.L4_Name_en
    channels={};graphs={};overview={};node_rows=[];edge_rows=[]
    for channel,n in [('AIM',10449),('AIID',1751)]:
        r=records[records.channel==channel]
        e=top[top.canonical_incident_id.isin(r.canonical_incident_id)]
        counts=Counter(e.L4_ID)
        g=nx.Graph();g.add_nodes_from(sorted(counts))
        pairs=Counter();cross=0
        for _,group in e.groupby('canonical_incident_id',sort=True):
            ids=sorted(group.L4_ID)
            cross+=len({cards[i]['L1_ID'] for i in ids})>1
            pairs.update(combinations(ids,2))
        for (a,b),count in sorted(pairs.items()):
            g.add_edge(a,b,count=count,weight=count/n*1000)
        assert g.number_of_nodes()==(516 if channel=='AIM' else 459)
        assert g.number_of_edges()==(7052 if channel=='AIM' else 2808)
        candidates=set()
        for domain in DOMAINS:
            ranked=sorted((i for i in g if cards[i]['L1_ID']==domain),key=lambda i:(-counts[i],i))
            candidates.update(ranked[:25])
        candidates.add(BRIDGE)
        induced=sorted(((a,b,g[a][b]['count']) for a,b in g.edges if a in candidates and b in candidates),key=lambda e:(-e[2],e[0],e[1]))[:240]
        shown=set(i for a,b,_ in induced for i in (a,b))
        overview[channel]={'ids':sorted(shown),'edges':[[a,b] for a,b,_ in induced]}
        degree_centrality=nx.degree_centrality(g)
        betweenness_centrality=nx.betweenness_centrality(g,normalized=True,weight=None,endpoints=False)
        nodes=[]
        for i in sorted(g):
            c=cards[i];activation=counts[i]
            node={'id':i,'name':c['L4_Name_en'],'name_ko':c['L4_Name_ko'],'definition':c['Risk_Definition_en'],'domain':c['L1_ID'],'family':c['L3_Name_en'],'color':color[i],'degree':g.degree(i),'degree_centrality':degree_centrality[i],'betweenness_centrality':betweenness_centrality[i],'activations':activation}
            nodes.append(node)
            node_rows.append({'channel':channel,**{k:v for k,v in node.items() if k not in ['definition','color']}})
        links=[]
        for a,b,d in sorted(g.edges(data=True)):
            link={'source':a,'target':b,'count':d['count'],'per_1000':round(d['weight'],6),'cross_domain':cards[a]['L1_ID']!=cards[b]['L1_ID']}
            links.append(link);edge_rows.append({'channel':channel,**link})
        crossing=sum(x['cross_domain'] for x in links)
        domain_counts={d:sum(counts[i] for i in counts if cards[i]['L1_ID']==d) for d in DOMAINS}
        ratios={d:(domain_counts[d]/(3*n))/(sum(c['L1_ID']==d for c in inventory)/622) for d in DOMAINS}
        channels[channel]={'n':n,'embodied_n':int(r.embodied_rule.sum()),'cross_incidents':int(cross),'cross_rate':cross/n,'node_count':len(nodes),'edge_count':len(links),'cross_edge_rate':crossing/len(links),'assortativity':None,'snapshot':str(r.source_snapshot.iloc[0]),'year_min':int(r.event_year.min()),'year_max':int(r.event_year.max()),'domain_assignments':domain_counts,'revelation_ratios':ratios,'nodes':nodes,'edges':links,'overview':overview[channel]}
        nx.set_node_attributes(g,{i:cards[i]['L1_ID'] for i in g},'domain')
        channels[channel]['assortativity']=float(nx.attribute_assortativity_coefficient(g,'domain'))
        graphs[channel]=g
    max_degree=max(n['degree'] for c in channels.values() for n in c['nodes'])
    radii={i:max(4,np.sqrt(16+(289-16)*max(graphs[c].degree(i) if i in graphs[c] else 0 for c in graphs)/max_degree)) for i in set().union(*[set(g) for g in graphs.values()])}
    union=nx.Graph()
    for g in graphs.values():
        union.add_nodes_from(g)
        for a,b,d in g.edges(data=True):
            if union.has_edge(a,b):union[a][b]['weight']+=d['weight']
            else:union.add_edge(a,b,weight=d['weight'])
    overview_ids=set().union(*[set(v['ids']) for v in overview.values()])
    small=union.subgraph(overview_ids).copy()
    layouts={'overview':shared_layout(small,radii),'all':shared_layout(union,radii)}
    metrics_path=args.inputs/'T1_revealed_network.csv'
    metrics=pd.read_csv(metrics_path)
    for ch in channels:
        row=metrics[metrics.channel==ch].iloc[0]
        assert np.isclose(channels[ch]['cross_edge_rate'],row.cross_edge_rate)
        assert np.isclose(channels[ch]['assortativity'],row.assortativity_r)
        channels[ch]['permutation_OE']=float(row.O_over_E)
    payload={'version':'20261025-channels-2','seed':SEED,'inventory':{'cards':622,'families':55,'domains':{'L1_G':491,'L1_A':68,'L1_P':63}},'domain_colors':semantic['l1_colors'],'bridge':BRIDGE,'max_degree':max_degree,'max_edge_rate':max(e['per_1000'] for c in channels.values() for e in c['edges']),'layouts':layouts,'channels':channels,'provenance':{'analytic_records_sha256':digest(recpath),'frozen_edges_sha256':digest(edgepath),'inventory_sha256':digest(ROOT/'data/heart_l4_risk_cards.json'),'semantic_style_sha256':digest(ROOT/'data/semantic_space.json'),'mapping':'BGE-M3 dense cosine, non-circular title + description + AI-system, top three','network':'Undirected unweighted topology, with co-activation counts retained as edge attributes'}}
    out=ROOT/'data/incidents/channels';out.mkdir(parents=True,exist_ok=True)
    (out/'networks.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
    for name,rows in [('nodes.csv',node_rows),('edges.csv',edge_rows)]:
        with (out/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    validation={'status':'passed','seed':SEED,'input_hashes':payload['provenance'],'incident_counts':{ch:c['n'] for ch,c in channels.items()},'assignments':{ch:c['n']*3 for ch,c in channels.items()},'active_cards':{ch:c['node_count'] for ch,c in channels.items()},'edges':{ch:c['edge_count'] for ch,c in channels.items()},'checks':['622 cards and 55-family release','channel counts 10449 and 1751','three unique candidate cards per incident','card IDs, names and domains match published inventory','network nodes, edges, cross-edge shares and assortativity match paper outputs','no raw incident text or adjudication fields in payload'],'display':{'selection':'25 highest-degree cards per domain, then 240 strongest induced links; remove displayed isolates','layout':'joint force layout shared across both channels; collision separation; seed 20261021','node_size':'area proportional to full-channel degree with minimum area','edge_width':'co-activation count per 1000 channel incidents; shared scale','edge_shape':'quadratic curves with 0.22 perpendicular midpoint displacement','colors':'exact L4 fills and L1 legend colors from existing AI risk space'}}
    (out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({ch:{k:v for k,v in c.items() if k not in ['nodes','edges','overview']} for ch,c in channels.items()},indent=2))

if __name__=='__main__':main()
