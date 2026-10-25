#!/usr/bin/env python3
"""Join frozen top-three card assignments to the existing public source summaries."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);args=parser.parse_args()
    source_path=ROOT/'data/incidents/downloads/source_records.csv.gz'
    source=pd.read_csv(source_path,dtype={'source_record_id':str},low_memory=False)
    source=source[source.source.isin(['OECD AIM','AIID'])].copy()
    source['canonical_incident_id']=source.source.map({'OECD AIM':'AIM','AIID':'AIID'})+':'+source.source_record_id
    records=pd.read_csv(args.inputs/'channel_analytic_records.csv.gz')
    edges=pd.read_csv(args.inputs/'channel_edges_k5.csv.gz');top=edges[edges['rank']<=3]
    merged=records.merge(source,on='canonical_incident_id',validate='one_to_one',suffixes=('','_source'))
    assert len(merged)==12200
    def text_hash(row):
        text='\n'.join(str(x).strip() for x in [row.incident_title,row.risk_description,row.ai_system] if pd.notna(x) and str(x).strip())
        return hashlib.sha256(text.encode()).hexdigest()
    assert merged.apply(text_hash,axis=1).eq(merged.mapping_text_sha256).all()
    networks=json.loads((ROOT/'data/incidents/channels/networks.json').read_text())
    provenance={'source_records_sha256':sha(source_path),'channel_records_sha256':sha(args.inputs/'channel_analytic_records.csv.gz'),'mapping_sha256':sha(args.inputs/'channel_edges_k5.csv.gz'),'exact_text_hash_matches':12200,'channels':{}}
    for channel,n in [('AIM',10449),('AIID',1751)]:
        selected=merged[merged.channel==channel].sort_values(['event_date','canonical_incident_id'],ascending=[False,True]).reset_index(drop=True)
        assert len(selected)==n
        rows=[];lookup={}
        for i,row in selected.iterrows():
            url=str(row.source_url).strip();parsed=urlparse(url)
            assert parsed.scheme=='https' and parsed.hostname in ['oecd.ai','incidentdatabase.ai']
            assert pd.notna(row.incident_title) and pd.notna(row.risk_description)
            expected=('https://oecd.ai/en/incidents/'+row.source_record_id if channel=='AIM' else 'https://incidentdatabase.ai/cite/'+row.source_record_id)
            assert url==expected
            lookup[row.canonical_incident_id]=i
            rows.append({'id':row.canonical_incident_id,'title':str(row.incident_title),'description':str(row.risk_description),'date':str(row.event_date) if pd.notna(row.event_date) else '', 'url':url})
        by_card=defaultdict(list)
        for _,edge in top[top.canonical_incident_id.isin(lookup)].iterrows():by_card[edge.L4_ID].append(lookup[edge.canonical_incident_id])
        by_card={k:sorted(set(v)) for k,v in sorted(by_card.items())}
        for node in networks['channels'][channel]['nodes']:assert len(by_card[node['id']])==node['activations']
        payload={'version':'20261025-details-1','channel':channel,'n':n,'source':('OECD AI Incidents Monitor' if channel=='AIM' else 'AI Incident Database'),'attribution':('OECD.AI incident summaries. Underlying source articles retain their rights.' if channel=='AIM' else 'AI Incident Database, CC BY-SA 4.0. Underlying reports retain their rights.'),'records':rows,'by_card':by_card}
        target=ROOT/f'data/incidents/channels/incidents-{channel}.json';target.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
        provenance['channels'][channel]={'records':n,'linked_cards':len(by_card),'sha256':sha(target),'bytes':target.stat().st_size}
    target=ROOT/'data/incidents/channels/incident_details_validation.json';target.write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(provenance['channels'],indent=2))

if __name__=='__main__':main()
