# Evidence PDF access review

Reviewed on 10 October 2026 by two specialist agents and the lead reviewer.
Scope: website and CSV, JSON and Excel release access links. Original source
URLs remain in source_snapshot and evidence_pdf_url_map.json. Paper attribution,
DOIs, excerpts and risk definitions are unchanged. Source-file hashes are
refreshed after the URL-only update; graph positions, links, embeddings,
colour shades and filter memberships are unchanged.

Both reviewers opened the proposed full texts and checked paper identity.
These eight alternatives affect 231 current card access links.

| Existing source | Verified PDF | Decision |
| --- | --- | --- |
| arXiv 2502.14143 abstract | https://arxiv.org/pdf/2502.14143 | Same paper, title verified |
| arXiv 2410.23472 abstract | https://arxiv.org/pdf/2410.23472 | Same paper, title verified |
| arXiv DOI 1511.03246 | https://arxiv.org/pdf/1511.03246 | Same ID and author; title uses AI instead of Artificial Intelligence |
| arXiv 2407.01294 abstract | https://arxiv.org/pdf/2407.01294 | Same paper, title verified |
| arXiv 2406.13843 abstract | https://arxiv.org/pdf/2406.13843 | Same paper, title verified |
| arXiv 2503.05731 abstract | https://arxiv.org/pdf/2503.05731 | Same paper, title verified |
| ICML 2025 workshop page 51008 | https://arxiv.org/pdf/2402.04247 | Same title and arXiv DOI; workshop poster, not a main-conference publication |
| SSRN abstract 5030173 | https://arxiv.org/pdf/2412.07780 | Same title, eight authors and 34 pages; oversight/intervention excerpt checked in Table 5 |

Official AIES DOI 10.1609/aies.v8i2.36655 and Springer chapter DOI
10.1007/978-981-99-9836-4_27 are retained despite arXiv counterparts.
Other journal and institutional report links are retained. No exact arXiv
counterpart was established for SSRN 4629460 or 4918704, so those links remain.
arXiv access does not itself establish peer review or methodological quality.
The user's example 2306.05499 is not substituted for unrelated cited works.

Implementation: assets/evidence-pdf-links.js applies an explicit allowlist in
both exploration views. The dataset builder uses the same verified mapping
from data/evidence_pdf_url_map.json. No broad DOI-to-arXiv guessing is performed.

The eight PDF URLs were reopened on 10 October 2026, each returning
application/pdf with the corresponding paper. CSV and JSON were compared
field-by-field with Excel for all 622 cards. The 231 URL replacements are
the only card-data changes. Before-edit release files are backed up locally.
