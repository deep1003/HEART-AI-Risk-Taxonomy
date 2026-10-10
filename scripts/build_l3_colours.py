"""Taxonomy-preserving, L1-anchored semantic L3 colours."""
import colorsys
import csv
import hashlib
import json
from pathlib import Path
import urllib.request
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = {'L1_G': '#4263eb', 'L1_A': '#d87518', 'L1_P': '#00977e'}


def api(endpoint, payload=None):
    request = urllib.request.Request('http://127.0.0.1:11434/api/' + endpoint,
                                    data=json.dumps(payload).encode() if payload else None,
                                    headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def main():
    cards_raw = (ROOT / 'data/heart_l4_risk_cards.json').read_bytes()
    cards = json.loads(cards_raw)
    hierarchy = {}
    sources = {}
    for path in sorted((ROOT / 'source_snapshot').glob('*_AI_Risk_L4_Master.csv')):
        sources[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                record = {key: row[key] for key in ('L1_ID', 'L1_Title_en', 'L2_ID', 'L2_Title_en',
                                                   'L3_ID', 'L3_Title_en', 'L3_Description_en')}
                if row['L3_ID'] in hierarchy:
                    assert hierarchy[row['L3_ID']] == record, 'Inconsistent master L3 rows'
                hierarchy[row['L3_ID']] = record
    records = [hierarchy[key] for key in sorted(hierarchy)]
    assert len(records) == 47
    for card in cards:
        row = hierarchy[card['L3_ID']]
        assert card['L1_ID'] == row['L1_ID'] and card['L2_ID'] == row['L2_ID']
        assert card['L3_Name_en'] == row['L3_Title_en']
    texts = [f"{row['L3_Title_en']}. {row['L3_Description_en']}" for row in records]
    text_hash = hashlib.sha256(json.dumps(texts).encode()).hexdigest()
    revision = str(np.load(ROOT / 'data/semantic_embeddings.npz')['model_revision'])
    cache_path = ROOT / f'data/l3_embeddings_{text_hash[:12]}.npz'
    if cache_path.exists():
        cache = np.load(cache_path, allow_pickle=False)
        assert str(cache['model_revision']) == revision
        vectors = cache['vectors']
    else:
        assert next(item for item in api('tags')['models'] if item['name'] == 'bge-m3:latest')['digest'] == revision
        vectors = []
        for start in range(0, len(texts), 4):
            vectors.extend(api('embed', {'model': 'bge-m3:latest', 'input': texts[start:start+4],
                                        'truncate': False, 'keep_alive': '5m'})['embeddings'])
        vectors = np.asarray(vectors, dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        np.savez_compressed(cache_path, vectors=vectors, ids=np.array([row['L3_ID'] for row in records]),
                            model_revision=revision, text_sha256=text_hash)
    domains = sorted(BASE)
    centroids = np.array([vectors[[i for i, row in enumerate(records) if row['L1_ID'] == domain]].mean(axis=0)
                          for domain in domains])
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
    affinities = vectors @ centroids.T
    # Deterministic within-domain PCA provides a smooth semantic colour coordinate.
    coordinates = np.zeros((47, 2))
    for domain in domains:
        indexes = [i for i, row in enumerate(records) if row['L1_ID'] == domain]
        centred = vectors[indexes] - vectors[indexes].mean(axis=0)
        _, _, components = np.linalg.svd(centred, full_matrices=False)
        for component in range(2):
            axis = components[component]
            if axis[np.argmax(np.abs(axis))] < 0:
                axis = -axis
            values = centred @ axis
            scale = max(float(np.max(np.abs(values))), 1e-9)
            coordinates[indexes, component] = values / scale
    palette = []
    for i, row in enumerate(records):
        own = domains.index(row['L1_ID'])
        competing = [index for index in range(3) if index != own]
        nearest = max(competing, key=lambda index: affinities[i, index])
        margin = float(affinities[i, own] - affinities[i, nearest])
        # Stronger boundary blending; the assigned domain remains the anchor.
        blend = float(.35 / (1 + np.exp(margin / .05)))
        rgb = np.array([int(BASE[row['L1_ID']][j:j+2], 16) / 255 for j in (1, 3, 5)])
        other = np.array([int(BASE[domains[nearest]][j:j+2], 16) / 255 for j in (1, 3, 5)])
        # Blend in linear-light RGB, then gently vary hue/lightness within L1.
        linear = lambda value: np.where(value <= .04045, value / 12.92, ((value + .055) / 1.055) ** 2.4)
        mixed = (1 - blend) * linear(rgb) + blend * linear(other)
        mixed = np.where(mixed <= .0031308, mixed * 12.92, 1.055 * mixed ** (1 / 2.4) - .055)
        hue, light, saturation = colorsys.rgb_to_hls(*mixed)
        hue = (hue + coordinates[i, 0] * .095) % 1
        light = np.clip(light + coordinates[i, 1] * .10, .32, .62)
        saturation = np.clip(saturation + coordinates[i, 0] * .12, .55, .95)
        colour = '#' + ''.join(f'{round(value * 255):02x}' for value in colorsys.hls_to_rgb(hue, light, saturation))
        palette.append(dict(row, color=colour, nearest_other_l1=domains[nearest],
                            boundary_blend=round(blend, 6), domain_cosines=dict(zip(domains, map(float, affinities[i]))),
                            semantic_colour_coordinates=coordinates[i].tolist()))
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -1)
    seed_colours = [row['color'] for row in palette]
    for i, row in enumerate(palette):
        neighbour = int(np.argmax(similarities[i]))
        weight = float(.45 / (1 + np.exp(-(similarities[i, neighbour] - .65) / .05)))
        first = np.array([int(seed_colours[i][j:j+2],16)/255 for j in (1,3,5)])
        second = np.array([int(seed_colours[neighbour][j:j+2],16)/255 for j in (1,3,5)])
        # HLS shortest-arc interpolation retains vivid mixed boundary colours.
        h1,l1,s1 = colorsys.rgb_to_hls(*first)
        h2,l2,s2 = colorsys.rgb_to_hls(*second)
        delta = (h2-h1+.5) % 1 - .5
        end = colorsys.hls_to_rgb((h1+weight*delta)%1, (1-weight)*l1+weight*l2, (1-weight)*s1+weight*s2)
        row.update(gradient_start=seed_colours[i],
                   gradient_end='#'+''.join(f'{round(value*255):02x}' for value in end),
                   neighbour_l3=records[neighbour]['L3_ID'], neighbour_cosine=float(similarities[i,neighbour]),
                   neighbour_mix_weight=weight)
    assert len({row['color'] for row in palette}) == 47
    result = {'source_sha256': hashlib.sha256(cards_raw).hexdigest(), 'master_sources': sources,
              'model_revision': revision, 'text_sha256': text_hash, 'embedding_file': cache_path.name,
              'base_colors': BASE, 'categories': palette,
              'method': 'BGE-M3 L3 title+definition; L1 centroid boundary blend up to 35%; within-L1 PCA hue ±34.2 degrees/lightness ±0.10/saturation ±0.12; node gradients toward the closest semantic L3 colour, shortest-arc HLS mixture up to 45%.',
              'limitations': 'Semantic colour proximity is approximate, not a distance-preserving map or classification confidence. Cross-domain colour does not change human-approved L1/L2/L3 assignments. No claim of 47 perceptually distinguishable classes.'}
    (ROOT / 'data/l3_semantic_colours.json').write_text(json.dumps(result, indent=2))
    assert (ROOT / 'data/heart_l4_risk_cards.json').read_bytes() == cards_raw
    print('Built 47 distinct L3 colours with 3 fixed L1 anchors; master assignments unchanged.')


if __name__ == '__main__':
    main()
