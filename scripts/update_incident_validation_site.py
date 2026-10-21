#!/usr/bin/env python3
"""Render incident-validation evidence and insert it into incidents.html."""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/incidents/validation"
FIGURES = ROOT / "assets/incident-figures"
START = "<!-- INCIDENT_VALIDATION_START -->"
END = "<!-- INCIDENT_VALIDATION_END -->"


def pct(value: float) -> str:
    return f"{100*value:.1f}%"


def null_svg(summary: dict) -> str:
    null = summary["incident_null"]
    observed, mean, p95 = (100*null[k] for k in ["observed_cross_domain_rate", "null_mean", "null_p95"])
    width, height = 1000, 430
    left, right, top, bottom = 210, 70, 95, 75
    plot = width-left-right
    def x(v): return left + plot*v/60
    rows = [("Observed embodied subset", observed, "#d84a4a"),
            ("Null mean", mean, "#5b88b5"), ("Null 95th percentile", p95, "#163b70")]
    body = []
    for i, (label, value, color) in enumerate(rows):
        y = top + 75*i
        body.append(f'<text x="{left-18}" y="{y+13}" text-anchor="end">{html.escape(label)}</text>')
        body.append(f'<rect x="{left}" y="{y-8}" width="{x(value)-left:.1f}" height="30" fill="{color}" rx="2"/>')
        body.append(f'<text x="{x(value)+12:.1f}" y="{y+13}" font-weight="700">{value:.1f}%</text>')
    ticks = []
    for value in range(0, 61, 10):
        xpos=x(value); ticks.append(f'<line x1="{xpos:.1f}" y1="{top-28}" x2="{xpos:.1f}" y2="{top+190}" stroke="#dde3ea"/>')
        ticks.append(f'<text x="{xpos:.1f}" y="{top+220}" text-anchor="middle">{value}%</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Embodied incident cross-domain mapping compared with a shuffled null</title>
<desc id="desc">Observed cross-domain mapping is {observed:.1f} percent, compared with a null mean of {mean:.1f} percent and a null 95th percentile of {p95:.1f} percent.</desc>
<style>text{{font-family:Arial,sans-serif;fill:#172a46;font-size:18px}}</style>
<rect width="100%" height="100%" fill="white"/>
<text x="55" y="42" font-size="27" font-weight="700">Embodied incidents cross HEART domains more often than shuffled mappings</text>
<text x="55" y="72" fill="#667085">Share with at least two HEART L1 domains; higher values mean more cross-domain activation</text>
{''.join(ticks)}{''.join(body)}
<text x="{left}" y="{height-28}" fill="#667085">2,000 rank × cosine-decile permutations; one-sided p = {null['one_sided_p']:.4f}</text>
</svg>'''


def table_rows(frame: pd.DataFrame, columns: list[tuple[str, str]], n: int = 10) -> str:
    rows=[]
    for _, row in frame.head(n).iterrows():
        cells=[]
        for key, kind in columns:
            value=row[key]
            if kind == "code": value=f"<code>{html.escape(str(value))}</code>"
            elif kind == "float": value=f"{float(value):.3f}"
            elif kind == "pct": value=pct(float(value))
            elif kind == "int": value=f"{int(value):,}"
            else: value=html.escape(str(value))
            cells.append(f"<td>{value}</td>")
        rows.append("<tr>"+"".join(cells)+"</tr>")
    return "".join(rows)


def main() -> None:
    summary=json.loads((DATA/"validation_summary.json").read_text())
    external=pd.read_csv(DATA/"external_label_validation.csv")
    bridges=pd.read_csv(DATA/"bridge_analysis_k3_k5.csv")
    hubs=pd.read_csv(DATA/"hubness_residuals.csv").sort_values("residual_rank")
    benign=pd.read_csv(DATA/"benign_intent_cases.csv")
    FIGURES.mkdir(parents=True,exist_ok=True)
    (FIGURES/"embodied-null-validation.svg").write_text(null_svg(summary))

    ext_rows=table_rows(external, [("validation_test","text"),("n","int"),("precision","pct"),("recall","pct"),("mcc","float")],4)
    incident_bridges=bridges[(bridges.network=="incident") & (bridges["k"]==3)].head(6)
    semantic_bridges=bridges[(bridges.network=="semantic") & (bridges["k"]==3)].head(6)
    bridge_rows=""
    for label, frame in [("Incident co-occurrence",incident_bridges),("Semantic",semantic_bridges)]:
        for _, row in frame.head(5).iterrows():
            bridge_rows += (f'<tr><td>{label}</td><td><code>{html.escape(row.L4_ID)}</code></td>'
                            f'<td>{html.escape(row.L4_Name_en)}</td><td>{row.betweenness:.3f}</td>'
                            f'<td>{100*row.cross_domain_share:.1f}%</td></tr>')
    hub_rows=table_rows(hubs, [("residual_rank","int"),("raw_degree_rank","int"),("L4_ID","code"),
                               ("L4_Name_en","text"),("incident_degree_k3","int"),("hubness_residual","float")],8)
    chosen=[160,693,227,1028,1441,1469]
    benign["numeric_id"]=benign.canonical_incident_id.str.replace("AIID:","",regex=False).astype(int)
    cases=benign.set_index("numeric_id").loc[chosen].reset_index()
    case_rows="".join(
        f'<tr><td><a href="{html.escape(row.source_url)}" target="_blank" rel="noopener">AIID {int(row.numeric_id)}</a></td>'
        f'<td>{html.escape(row.incident_title)}</td><td>{html.escape(row.case_type)}</td></tr>' for _,row in cases.iterrows())

    section=f'''{START}
<section id="validation"><h2>Cross-domain incident structure survives a non-circular validation design</h2>
<p class="chart-subtitle">The validation mapping embeds only incident title, narrative and AI-system description; source risk and harm labels are held out. Positive evidence means independent labels recover the expected HEART domain, not that every individual card is correct.</p>
<div class="status-callout"><strong>Human review is prepared, not completed.</strong> A frozen 150-incident stratified sample contains 84 embodied candidates and blank adjudication fields for the relevance of each top-three card. A separate 100-case embodied-rule audit is also frozen. Until a human reviewer completes them, the site does not claim human-validated mapping accuracy.</div>
<figure><img src="assets/incident-figures/embodied-null-validation.svg" alt="Observed embodied cross-domain rate compared with shuffled null baselines"><figcaption><strong>Notes:</strong> The provisional embodied rule identifies 1,344 candidates using strong MIT/CSET physical-system labels or contextual physical-system text, with explicit exclusions for names such as Cook and for deepfake/content false positives. The observed cross-domain share is 52.3%, not the previously assumed 55.0%. The null permutes card assignments within rank and cosine-decile strata, retaining the similarity distribution. The observed value exceeds every one of 2,000 shuffled draws (one-sided p=0.0005). The embodied definition remains provisional until the 100-case audit is adjudicated. <a href="data/incidents/validation/validation_summary.json">Data</a></figcaption></figure>

<h3>Independent source labels give uneven, informative support</h3>
<div class="table-wrap"><table><thead><tr><th>Held-out validation label</th><th>Eligible incidents</th><th>Precision</th><th>Recall</th><th>MCC</th></tr></thead><tbody>{ext_rows}</tbody></table></div>
<p>MIT physical-goal labels provide the strongest external check (precision 65.5%, recall 74.7%, MCC 0.665). CSET physical-system labels are highly precise but incomplete; AIM physical-harm labels have broader coverage but low recall for Physical-AI cards because physical harm can arise from non-embodied systems. MIT agent labels only weakly recover Agentic HEART cards, signalling that behaviour labels and HEART's risk-domain ontology are not interchangeable.</p>

<h3>Different cards bridge semantic proximity and reported co-occurrence</h3>
<p class="chart-subtitle">Betweenness measures how often a card lies on shortest paths; cross-domain share reports the fraction of its neighbours outside its own General, Agentic or Physical domain.</p>
<div class="table-wrap"><table><thead><tr><th>Network</th><th>HEART ID</th><th>Risk card</th><th>Betweenness</th><th>Cross-domain neighbours</th></tr></thead><tbody>{bridge_rows}</tbody></table></div>
<p>Automated-driving control-transfer failure is the leading incident-network bridge at both k=3 and k=5, with nearly nine in ten neighbours in other L1 domains. In the semantic network, threats and intimidation and systemic regulatory failure occupy central paths, while existential and catastrophic risk has the strongest cross-domain bridging among the leading semantic cards. Full k=3 and k=5 rankings are downloadable.</p>

<h3>Generic wording explains some hubness, but not the leading incident hubs</h3>
<p class="chart-subtitle">Residual rank removes the association between log incident degree and similarity to the all-card semantic centroid, with HEART L1 fixed effects; a high positive residual means more incident connections than textual generality predicts.</p>
<div class="table-wrap"><table><thead><tr><th>Residual rank</th><th>Raw rank</th><th>HEART ID</th><th>Risk card</th><th>Incidents</th><th>Residual</th></tr></thead><tbody>{hub_rows}</tbody></table></div>
<p>Centroid similarity is strongly associated with raw hub degree (model R²={summary['hubness_control']['r_squared']:.3f}; centroid p&lt;0.001), confirming a hubness artifact. Yet deepfake harassment remains first after adjustment, and automated-driving control-transfer rises from raw rank 9 to residual rank 2. These are not merely generic-card effects.</p>

<h3>Benign requests can still lead to harmful execution</h3>
<p class="chart-subtitle">Cases are database-reported examples in which an assistant or agent pursued an ordinary request, misunderstood it, exceeded authority or supplied unsafe help; they are not independent causal adjudications.</p>
<div class="table-wrap"><table><thead><tr><th>Incident</th><th>Reported case</th><th>Screening category</th></tr></thead><tbody>{case_rows}</tbody></table></div>
<p>No incident literally involving a microwave was found. The closest reported analogues are Alexa recommending the electrical “penny challenge”, Google AI returning dangerous cooking and cleaning advice, Waze directing a vehicle into a lake, Operator purchasing groceries without authorisation, and Claude/Cursor agents deleting user or production data while carrying out organisational or staging tasks.</p>

<h3>Validation downloads</h3><ul class="downloads">
<li><a href="data/incidents/validation/human_validation_sample_150.csv">Frozen 150-case human-validation sheet</a></li>
<li><a href="data/incidents/validation/embodied_rule_audit_sample_100.csv">Frozen 100-case embodied-rule audit</a></li>
<li><a href="data/incidents/validation/noncircular_incident_heart_edges_k5.csv.gz">Non-circular incident–HEART mappings</a></li>
<li><a href="data/incidents/validation/external_label_validation.csv">External-label validation metrics</a></li>
<li><a href="data/incidents/validation/bridge_analysis_k3_k5.csv">Semantic and incident bridge rankings</a></li>
<li><a href="data/incidents/validation/hubness_residuals.csv">Raw and residual hub rankings</a></li>
<li><a href="data/incidents/validation/benign_intent_cases.csv">Benign-intent screening candidates</a></li>
</ul></section>
{END}'''
    page=ROOT/"incidents.html"
    text=page.read_text()
    if START in text and END in text:
        before=text.split(START,1)[0]; after=text.split(END,1)[1]
        text=before+section+after
    else:
        marker='<section><h2>Methods, provenance and limitations</h2>'
        if marker not in text: raise RuntimeError("Insertion marker not found")
        text=text.replace(marker,section+"\n"+marker,1)
    text=text.replace('assets/incidents.css?v=20261021','assets/incidents.css?v=20261021-2')
    page.write_text(text)
    print(json.dumps({"page":str(page),"svg":str(FIGURES/"embodied-null-validation.svg")},indent=2))


if __name__ == "__main__":
    main()
