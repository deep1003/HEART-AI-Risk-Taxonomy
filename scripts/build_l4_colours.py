"""Deterministic per-L4 solid colours from existing semantic embeddings."""
import colorsys
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = (ROOT / 'data/heart_l4_risk_cards.json').read_bytes()
    cards = sorted(json.loads(raw), key=lambda card: card['L4_ID'])
    palette = json.loads((ROOT / 'data/l3_semantic_colours.json').read_text())
    l4 = np.load(ROOT / 'data/semantic_embeddings.npz', allow_pickle=False)
    l3 = np.load(ROOT / 'data' / palette['embedding_file'], allow_pickle=False)
    assert palette['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert l4['ids'].tolist() == [card['L4_ID'] for card in cards]
    assert str(l4['model_revision']) == str(l3['model_revision']) == palette['model_revision']
    categories = palette['categories']
    assert l3['ids'].tolist() == [row['L3_ID'] for row in categories]
    scores = l4['vectors'] @ l3['vectors'].T
    coordinates = np.zeros((len(cards), 3))
    for category in categories:
        indexes = [i for i, card in enumerate(cards) if card['L3_ID'] == category['L3_ID']]
        if len(indexes) < 2:
            continue
        centred = l4['vectors'][indexes] - l4['vectors'][indexes].mean(axis=0)
        _, singular, components = np.linalg.svd(centred, full_matrices=False)
        for component in range(min(3, len(indexes)-1)):
            if singular[component] < 1e-7:
                continue
            axis = components[component]
            if axis[np.argmax(np.abs(axis))] < 0:
                axis = -axis
            values = centred @ axis
            coordinates[indexes, component] = values / max(float(np.max(np.abs(values))), 1e-9)
    output = []
    for i, card in enumerate(cards):
        own = l3['ids'].tolist().index(card['L3_ID'])
        ranked = np.argsort(-scores[i], kind='stable')
        neighbour = next(int(index) for index in ranked if index != own)
        margin = float(scores[i, own] - scores[i, neighbour])
        weight = float(.30 / (1 + np.exp(margin / .06)))
        def hls(index):
            color = categories[index]['color']
            return colorsys.rgb_to_hls(*(int(color[j:j+2],16)/255 for j in (1,3,5)))
        h,l,s = hls(own)
        nh,nl,ns = hls(neighbour)
        h = (h + weight * ((nh-h+.5)%1-.5) + coordinates[i,0]*.055) % 1
        l = float(np.clip((1-weight)*l+weight*nl+coordinates[i,1]*.14,.30,.72))
        s = float(np.clip((1-weight)*s+weight*ns+coordinates[i,2]*.16,.45,.95))
        colour = '#' + ''.join(f'{round(value*255):02x}' for value in colorsys.hls_to_rgb(h,l,s))
        output.append({'id':card['L4_ID'], 'l3':card['L3_ID'], 'color':colour,
                       'semantic_coordinates':coordinates[i].tolist(),
                       'neighbour_l3':categories[neighbour]['L3_ID'], 'neighbour_mix_weight':weight,
                       'assigned_l3_cosine':float(scores[i,own]), 'neighbour_l3_cosine':float(scores[i,neighbour])})
    result = {'source_sha256':hashlib.sha256(raw).hexdigest(), 'model_revision':palette['model_revision'],
              'l3_palette_sha256':hashlib.sha256((ROOT/'data/l3_semantic_colours.json').read_bytes()).hexdigest(),
              'method':'Solid L4 colours: existing L3 seed; nearest other L3 definition blend up to 30%; within-assigned-L3 PCA hue ±19.8 degrees, lightness ±0.14, saturation ±0.16. All inputs are fixed semantic embeddings, not degree, severity, probability or random IDs.',
              'points':output}
    (ROOT/'data/l4_semantic_colours.json').write_text(json.dumps(result,indent=2))
    print(f"Built {len(output)} solid L4 colours, {len(set(row['color'] for row in output))} distinct RGB values; source unchanged.")
    assert (ROOT/'data/heart_l4_risk_cards.json').read_bytes() == raw


if __name__ == '__main__':
    main()
