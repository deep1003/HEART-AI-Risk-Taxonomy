"""Assemble reviewed concept definitions in the existing control order."""
import json
import shutil
from pathlib import Path
from build_semantic_space import TOPICS

ROOT = Path(__file__).resolve().parents[1]
reviewed = []
review_root = ROOT / 'data/keyword_review'
review_root.mkdir(exist_ok=True)
for reviewer in ('a', 'b'):
    filename = f'keyword_definitions_{reviewer}.json'
    working = ROOT / 'evidence_work' / filename
    if working.exists():
        shutil.copyfile(working, review_root / filename)
    reviewed.extend(json.loads((review_root / filename).read_text()))
by_id = {item['id']: item for item in reviewed}
domains = {
    'general-ai': ('L1_G', 'General-purpose AI systems whose primary inputs and outputs are digital content, including text, images, audio, video and code.'),
    'agentic-ai': ('L1_A', 'AI systems that pursue objectives through planning, tool use and actions with delegated operational autonomy.'),
    'physical-ai': ('L1_P', 'Embodied AI systems that sense and act in the physical world, including robots and autonomous machines.'),
}
result = []
for rule in TOPICS:
    if rule['id'] in domains:
        l1, definition = domains[rule['id']]
        item = dict(id=rule['id'], name=rule['name'], definition=definition,
                    scope='HEART operational domain description. Membership is determined exclusively by the existing human-approved L1 assignment, not these words or cosine similarity.',
                    mapping_mode='taxonomy', l1=l1, reference_title='HEART human-approved L1 taxonomy dataset',
                    url='data/heart_l4_risk_cards.csv', quote=rule['name'], quote_location='L1_Name_en column')
    else:
        item = dict(by_id[rule['id']])
        for prefix in ('Operational synthesis for HEART: ', 'Operational composite for HEART: ', 'Operational paraphrase of EU AI Act Article 3(60): '):
            if item['definition'].startswith(prefix):
                item['definition'] = item['definition'][len(prefix):]
        item.update(mapping_mode='semantic', threshold=0.60, review_include=[], review_exclude=[],
                    threshold_status='Exploratory initial threshold; not empirically calibrated accuracy',
                    verified_on='2026-10-10', source_review='Primary source and quote checked by an AI specialist reviewer; synthesis adjudicated by the lead agent. Not a new human-review round.')
        decisions = {}
        for reviewer in ('a', 'b'):
            filename = f'keyword_mapping_review_{reviewer}.json'
            working = ROOT / 'evidence_work' / filename
            if working.exists():
                shutil.copyfile(working, review_root / filename)
            if (review_root / filename).exists():
                decisions.update({entry['id']: entry for entry in json.loads((review_root / filename).read_text())})
        if item['id'] in decisions:
            decision = decisions[item['id']]
            item.update(threshold=decision['threshold'],
                        review_include=[entry['id'] for entry in decision['include']],
                        review_exclude=[entry['id'] for entry in decision['exclude']],
                        mapping_review=decision,
                        threshold_status='AI-specialist-reviewed exploratory threshold, not independently calibrated accuracy')
    result.append(item)
assert len(result) == 17 and len(by_id) == 14
(ROOT / 'data/keyword_definitions.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
