#!/usr/bin/env python3
"""Build the public Financial AI Agent to HEART L4 mapping table."""
from __future__ import annotations

import csv
import html
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "financial_ai_agent_heart_l4_mapping_final.csv"
OUTPUT = ROOT / "financial-ai-agent-mapping.html"


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def status_label(value: str) -> str:
    return {"accepted": "Accepted", "partial_match": "Partial match", "no_exact_match": "No exact match"}[value]


def card_html(row: dict[str, str]) -> str:
    if not row["l4_id"]:
        return '<div class="no-card"><strong>No exact current L4 match</strong><span>Mapping was intentionally withheld.</span></div>'
    domain_class = "agentic" if row["l1_id"] == "L1_A" else "general"
    score = f'{float(row["combined_score"]):.3f}' if row["combined_score"] else "Not scored"
    rank = f'Embedding rank {row["embedding_rank"]}' if row["embedding_rank"] else "Human adjudication"
    return (
        f'<div class="mapped-card {domain_class}">'
        f'<code>{esc(row["l4_id"])}</code>'
        f'<strong lang="ko">{esc(row["l4_name_ko"])}</strong>'
        f'<span>{esc(row["l4_name_en"])}</span>'
        f'<small>{esc(row["l3_id"])} · {esc(rank)} · retrieval score {esc(score)}</small>'
        '</div>'
    )


def main() -> None:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["criterion_no"], []).append(row)
    assert len(grouped) == 17
    assert sum(bool(row["l4_id"]) for row in rows) == 28
    assert len({row["l4_id"] for row in rows if row["l4_id"]}) == 23

    table_rows = []
    for criterion_no, criterion_rows in grouped.items():
        first = criterion_rows[0]
        cards = "".join(card_html(row) for row in criterion_rows)
        statuses = sorted({row["mapping_status"] for row in criterion_rows})
        status_html = "".join(
            f'<span class="mapping-status {esc(status)}">{esc(status_label(status))}</span>'
            for status in statuses
        )
        rationale = first["reviewer_rationale"]
        provenance = first["decision_provenance"].replace("_", " ")
        table_rows.append(f"""
          <tr>
            <td><span class="criterion-number">{esc(criterion_no)}</span></td>
            <td class="criterion-name"><strong lang="ko">{esc(first['criterion_label_ko'])}</strong><span>{esc(first['criterion_label_en'])}</span></td>
            <td class="risk-statement"><div lang="ko">{esc(first['risk_statement_ko'])}</div><div class="en">{esc(first['risk_statement_en'])}</div></td>
            <td><div class="mapped-cards">{cards}</div></td>
            <td>{status_html}</td>
            <td class="mapping-rationale"><span lang="ko">{esc(rationale)}</span><div class="mapping-provenance">{esc(provenance)}</div></td>
          </tr>""")

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Criterion-level mapping between the Financial Security Institute's 17 Financial AI Agent security criteria and HEART L4 risk cards.">
  <title>Financial AI Agent mapping | HEART</title>
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/styles-v2.css">
  <link rel="stylesheet" href="assets/institution.css">
  <link rel="stylesheet" href="assets/explorer-layout.css?v=shared-shell-20261010">
  <link rel="stylesheet" href="assets/application-mapping.css?v=financial-agent-20261012">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="./" aria-label="HEART home"><span class="heart-brand-copy"><span class="brand-kicker"><span class="brand-gold-dot" aria-hidden="true"></span>AI Risk Taxonomy for General, Agentic, and Physical AI</span><strong>HEA<span class="heart-brand-r">R</span>T</strong><small>Hybrid Evidence-based AI Risk Taxonomy</small></span></a>
    <nav aria-label="Primary navigation"><a href="https://github.com/deep1003/HEART-AI-Risk-Taxonomy" target="_blank" rel="noopener noreferrer">GitHub</a></nav>
  </header>
  <main>
    <nav class="section-nav" aria-label="Page sections"><div class="explorer-tabs"><a href="about.html?v=shared-shell-20261010">About HEART</a><a href="./?v=shared-shell-20261010#explore">AI risk taxonomy</a><a href="./?v=shared-shell-20261010#ai-risk-space">AI risk space</a><a href="financial-ai-agent-mapping.html" aria-current="page">Financial AI Agent mapping</a></div></nav>
    <div class="mapping-main">
      <section class="mapping-hero">
        <div>
          <p class="mapping-eyebrow">Application mapping record</p>
          <h1>Financial AI Agent security criteria mapped to HEART L4 risks</h1>
          <p class="mapping-lede">This record translates the Financial Security Institute's 17 security inspection criteria into risk statements and documents their reviewed correspondence with the frozen HEART inventory of 622 L4 risk cards.</p>
          <div class="mapping-actions"><a href="./?v=financial-agent-20261012#ai-risk-space">View in AI risk space</a><a class="secondary" href="data/financial_ai_agent_heart_l4_mapping_final.csv" download>Download mapping CSV</a><a class="secondary" href="https://www.fsec.or.kr/bbs/detail?menuNo=69&amp;bbsNo=12122" target="_blank" rel="noopener noreferrer">Open source criteria</a></div>
        </div>
        <div class="mapping-summary" aria-label="Mapping summary">
          <div><strong>17</strong><span>security criteria</span></div><div><strong>16</strong><span>criteria with a match</span></div><div><strong>28</strong><span>criterion to L4 links</span></div><div><strong>23</strong><span>unique L4 cards</span></div>
        </div>
      </section>
      <section class="mapping-method" aria-labelledby="method-title">
        <div><p class="mapping-eyebrow">Method</p><h2 id="method-title">Embedding retrieval followed by semantic adjudication</h2><p>The criteria were not assigned automatically by a fixed similarity cut-off. Sentence embeddings narrowed the search space; final decisions compared the risk mechanism, protected object and resulting harm.</p><div class="mapping-note"><strong>How to read the scores.</strong> Rank and score describe candidate retrieval only. They are not probabilities, severity estimates or mapping confidence. The 0.80 line achieved 100% precision but only 17.9% recall on reviewed pairs, so it was retained only as a high-priority review threshold.</div></div>
        <div class="mapping-steps"><div class="mapping-step"><strong>Risk reformulation</strong><span>Each control-oriented criterion was rewritten as the risk that arises when the control fails.</span></div><div class="mapping-step"><strong>Bilingual representation</strong><span>Korean and English names and statements were embedded with BGE-M3 in 1,024 dimensions.</span></div><div class="mapping-step"><strong>Weighted retrieval</strong><span>Similarity combined 0.60 Korean to Korean, 0.30 English to English, and 0.05 for each cross-language direction.</span></div><div class="mapping-step"><strong>Expert review</strong><span>Top candidates and the full master were reviewed by mechanism, protected object and harm; reviewers could add a lower-ranked direct match or abstain.</span></div><div class="mapping-step"><strong>Frozen-master control</strong><span>No L4 card was created, deleted, merged, renamed or reassigned for this application mapping.</span></div></div>
      </section>
      <section class="mapping-table-section" aria-labelledby="table-title">
        <p class="mapping-eyebrow">Criterion-level record</p><h2 id="table-title">17 criteria and their reviewed L4 mappings</h2><p class="mapping-table-intro">Each criterion remains a distinct source requirement. A criterion may map to several cards when the source risk contains different mechanisms or protected objects. The same L4 card may support more than one criterion.</p>
        <div class="mapping-legend"><span class="mapping-status accepted">Accepted</span><span class="mapping-status partial_match">Partial match</span><span class="mapping-status no_exact_match">No exact match</span></div>
        <div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th scope="col">No.</th><th scope="col">Evaluation criterion</th><th scope="col">Risk statement</th><th scope="col">Mapped HEART L4 cards</th><th scope="col">Outcome</th><th scope="col">Review rationale</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
        <div class="mapping-footnotes"><article><h3>Partial mappings</h3><p>Memory isolation maps only to cross-application data exfiltration, not benign session contamination. Kill-switch coverage maps only to an agent resisting shutdown or correction, not to the simple absence or technical failure of a kill switch.</p></article><article><h3>Abstention</h3><p>Resource exhaustion was left unmapped because the current HEART inventory has no exact card for unbounded loops or tool calls by a single agent. The process did not force a nearby but semantically different match.</p></article></div>
        <p class="mapping-source"><strong>Primary source:</strong> <a href="https://www.fsec.or.kr/bbs/detail?menuNo=69&amp;bbsNo=12122" target="_blank" rel="noopener noreferrer">Financial Security Institute, Financial-sector AI Agent Security Evaluation Criteria, 8 October 2026</a>. Mapping snapshot prepared 12 October 2026 against HEART's frozen 622-card inventory.</p>
      </section>
    </div>
  </main>
  <footer class="site-footer publisher-footer"><div class="publisher-identity"><a class="kt-logo-link" href="https://corp.kt.com/eng/" target="_blank" rel="noopener noreferrer" aria-label="KT Corporation official website"><img src="assets/kt-logo-light.svg" alt="KT" width="40" height="40"></a><div><p class="publisher-name">Frontier AI Lab, KT Corporation</p><a class="publisher-contact" href="mailto:responsible.ai@kt.com">responsible.ai@kt.com</a></div></div></footer>
</body>
</html>
"""
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(grouped)} criteria, 28 links, 23 unique L4 cards")


if __name__ == "__main__":
    main()
