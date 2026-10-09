"""Verify embedding provenance and every published edge; output text only."""
import hashlib
import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
data = json.loads((root/'data/semantic_space.json').read_text())
archive = np.load(root/'data/semantic_embeddings.npz', allow_pickle=False)
vectors = archive['vectors']
ids = archive['ids'].tolist()
assert vectors.shape == (622,384) and np.isfinite(vectors).all()
assert np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5)
assert len(set(ids))==622 and ids==[point['id'] for point in data['points']]
assert str(archive['text_sha256'])==data['method']['text_sha256']
assert str(archive['model_revision'])==data['method']['model_revision']
assert hashlib.sha256((root/'data/semantic_embeddings.npz').read_bytes()).hexdigest()==data['method']['embedding_sha256']
lookup = {risk:index for index,risk in enumerate(ids)}
cosine = vectors @ vectors.T
np.fill_diagonal(cosine,-1)
expected = set()
for index in range(len(ids)):
    for other in np.argsort(-cosine[index],kind='stable')[:8]:
        if cosine[index,other]>=.45:
            expected.add(tuple(sorted((index,int(other)))))
actual = set()
for a,b,weight in data['edges']:
    i,j=lookup[a],lookup[b]
    assert abs(float(cosine[i,j])-weight)<1e-6
    actual.add(tuple(sorted((i,j))))
assert expected==actual
assert len(actual)==len(data['edges'])
print(f'Embedding verification passed: {vectors.shape}, normalised vectors, pinned revision, exact nearest-neighbour union and all {len(actual)} cosine weights.')
