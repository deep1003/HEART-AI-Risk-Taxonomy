#!/usr/bin/env python3
"""Build publication-ready incident network figures and the HEART web page."""
from __future__ import annotations

import gzip
import html
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "processed"
DATA = ROOT / "data" / "incidents"
FIGURES = ROOT / "assets" / "incident-figures"
DOWNLOADS = DATA / "downloads"
COLORS = {"L1_G": "#173b6c", "L1_A": "#c84b4b", "L1_P": "#2a8f87"}


def save_figure(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, format="svg", bbox_inches="tight", metadata={"Date": "2026-10-21"})
    plt.close(fig)


def bipartite_figure() -> None:
    nodes = pd.read_csv(PROCESSED / "risk_network_nodes_k3.csv").nlargest(35, "incident_degree")
    top_risks = set(nodes.L4_ID)
    edges = pd.read_csv(PROCESSED / "incident_heart_edges_k5.csv")
    edges = edges[(edges.in_k3 == True) & edges.L4_ID.isin(top_risks)]  # noqa: E712
    counts = edges.groupby("canonical_incident_id").size().sort_values(ascending=False)
    incidents = set(counts.head(140).index)
    edges = edges[edges.canonical_incident_id.isin(incidents)]
    graph = nx.Graph()
    for _, row in nodes.iterrows():
        graph.add_node(row.L4_ID, kind="risk", label=row.L4_Name_en, l1=row.L1_ID)
    for incident in incidents:
        graph.add_node(incident, kind="incident")
    for _, row in edges.iterrows():
        graph.add_edge(row.canonical_incident_id, row.L4_ID, weight=row.cosine_similarity)

    risks = [node for node, data in graph.nodes(data=True) if data["kind"] == "risk"]
    cases = [node for node, data in graph.nodes(data=True) if data["kind"] == "incident"]
    risk_order = sorted(risks, key=lambda node: graph.degree(node), reverse=True)
    case_order = sorted(cases, key=lambda node: graph.degree(node), reverse=True)
    positions = {}
    for index, node in enumerate(case_order):
        positions[node] = (0, index / max(1, len(case_order) - 1))
    for index, node in enumerate(risk_order):
        positions[node] = (1, index / max(1, len(risk_order) - 1))

    fig, ax = plt.subplots(figsize=(13, 9))
    nx.draw_networkx_edges(graph, positions, ax=ax, alpha=0.10, width=0.55, edge_color="#64748b")
    nx.draw_networkx_nodes(graph, positions, nodelist=cases, node_size=12, node_color="#b8c0cc", ax=ax)
    for l1, color in COLORS.items():
        selected = [node for node in risks if graph.nodes[node]["l1"] == l1]
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=selected,
            node_size=[45 + 2.2 * graph.degree(node) for node in selected],
            node_color=color,
            edgecolors="white",
            linewidths=0.5,
            ax=ax,
        )
    for node in risk_order[:12]:
        label = graph.nodes[node]["label"]
        if len(label) > 54:
            label = label[:51] + "…"
        x, y = positions[node]
        ax.text(x + 0.025, y, label, va="center", fontsize=7.5, color="#18253a")
    ax.text(0, 1.035, "Incident nodes", ha="center", fontsize=11, fontweight="bold", color="#173b6c")
    ax.text(1, 1.035, "HEART L4 risk cards", ha="center", fontsize=11, fontweight="bold", color="#173b6c")
    ax.set_title("Reported incidents connect repeatedly to a small set of HEART risks", loc="left", fontsize=18, fontweight="bold", color="#173b6c", pad=26)
    ax.text(0, 1.075, "Filtered view: 140 incidents with the most links to the 35 most frequent k=3 cards; node size reflects displayed degree", transform=ax.transAxes, fontsize=10, color="#5f6670")
    ax.set_axis_off()
    save_figure(fig, "bipartite-network-k3.svg")


def cooccurrence_figure() -> None:
    nodes = pd.read_csv(PROCESSED / "risk_network_nodes_k3.csv").nlargest(55, "pagerank")
    chosen = set(nodes.L4_ID)
    edges = pd.read_csv(PROCESSED / "risk_cooccurrence_edges_k3.csv")
    edges = edges[edges.risk_a.isin(chosen) & edges.risk_b.isin(chosen)].copy()
    edges["display_weight"] = edges.association_strength * np.log1p(edges.cooccurrence_count)
    edges = edges.nlargest(180, "display_weight")
    graph = nx.Graph()
    for _, row in nodes.iterrows():
        graph.add_node(row.L4_ID, **row.to_dict())
    for _, row in edges.iterrows():
        graph.add_edge(row.risk_a, row.risk_b, **row.to_dict())
    positions = nx.spring_layout(graph, seed=23, weight="display_weight", k=0.55, iterations=250)
    fig, ax = plt.subplots(figsize=(12.5, 10))
    widths = [0.25 + 2.5 * graph[u][v]["display_weight"] for u, v in graph.edges]
    nx.draw_networkx_edges(graph, positions, width=widths, alpha=0.16, edge_color="#64748b", ax=ax)
    for l1, color in COLORS.items():
        selected = [node for node in graph if graph.nodes[node]["L1_ID"] == l1]
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=selected,
            node_size=[35 + graph.nodes[node]["incident_degree"] * 0.15 for node in selected],
            node_color=color,
            edgecolors="white",
            linewidths=0.7,
            alpha=0.94,
            ax=ax,
        )
    labelled = sorted(graph, key=lambda node: graph.nodes[node]["pagerank"], reverse=True)[:14]
    labels = {node: graph.nodes[node]["L4_ID"] for node in labelled}
    nx.draw_networkx_labels(graph, positions, labels=labels, font_size=7.5, font_color="#18253a", ax=ax)
    ax.set_title("Risk co-occurrence forms connected but modular communities", loc="left", fontsize=18, fontweight="bold", color="#173b6c", pad=25)
    ax.text(0, 1.02, "Top 55 PageRank risks and 180 strongest displayed ties; edge strength combines association and co-occurrence count", transform=ax.transAxes, fontsize=10, color="#5f6670")
    ax.set_axis_off()
    save_figure(fig, "risk-cooccurrence-network-k3.svg")


def degree_figure() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for k, color, marker in ((3, "#173b6c", "o"), (5, "#c84b4b", "s")):
        nodes = pd.read_csv(PROCESSED / f"risk_network_nodes_k{k}.csv")
        frequency = nodes.network_degree.value_counts().sort_index()
        ax.scatter(frequency.index, frequency.values, s=30, alpha=0.78, color=color, marker=marker, label=f"k={k}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Risk-card degree (log scale)")
    ax.set_ylabel("Number of risk cards (log scale)")
    ax.grid(True, which="both", color="#d7dbe1", linewidth=0.6, alpha=0.7)
    ax.legend(frameon=False)
    ax.set_title("Most risk cards are locally connected, while a minority act as network hubs", loc="left", fontsize=17, fontweight="bold", color="#173b6c", pad=18)
    ax.text(0, 1.02, "Degree counts distinct co-occurring HEART cards; both axes are logarithmic", transform=ax.transAxes, fontsize=10, color="#5f6670")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    save_figure(fig, "degree-distribution.svg")


def gzip_csv(source: Path, target: Path, columns: list[str] | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(source, low_memory=False, usecols=columns)
    with gzip.open(target, "wt", encoding="utf-8", newline="") as handle:
        data.to_csv(handle, index=False)


def build_downloads() -> None:
    common = [
        "source", "source_record_id", "record_uid", "canonical_aiid_id", "incident_title",
        "risk_name", "risk_description", "event_date", "event_year", "severity_raw",
        "severity_normalized", "severity_provenance", "harm_types", "harmed_entities",
        "countries", "industry_sector", "ai_system", "developer", "deployer", "actual_harm",
        "near_miss_possible", "source_url", "report_count", "source_license", "source_snapshot",
        "dedup_title_normalized", "dedup_date_bucket", "dedup_entity_tokens", "dedup_fingerprint",
    ]
    gzip_csv(PROCESSED / "source_records.csv", DOWNLOADS / "source_records.csv.gz", common)
    gzip_csv(PROCESSED / "incident_heart_edges_k5.csv", DOWNLOADS / "incident_heart_edges_k5.csv.gz")
    shutil.copy2(DATA / "incidents_compact.json", DOWNLOADS / "canonical_incidents_compact.json")
    for name in ("duplicate_candidates.csv", "risk_network_nodes_k3.csv", "risk_cooccurrence_edges_k3.csv", "network_metrics.json", "data_quality.json"):
        source = PROCESSED / name
        target = DOWNLOADS / name
        shutil.copy2(source, target)


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def table_rows(frame: pd.DataFrame, count: int = 8) -> str:
    rows = []
    for _, row in frame.head(count).iterrows():
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(row.L4_ID)}</code></td>"
            f"<td>{html.escape(row.L4_Name_en)}</td>"
            f"<td>{int(row.incident_degree):,}</td>"
            f"<td>{row.pagerank:.4f}</td>"
            f"<td>{row.betweenness:.4f}</td>"
            "</tr>"
        )
    return "".join(rows)


def build_page() -> None:
    quality = json.load(open(PROCESSED / "data_quality.json"))
    metrics = json.load(open(PROCESSED / "network_metrics.json"))
    k3 = metrics["k3"]
    k5 = metrics["k5"]
    nodes = pd.read_csv(PROCESSED / "risk_network_nodes_k3.csv").sort_values("incident_degree", ascending=False)
    bridges = pd.read_csv(PROCESSED / "risk_network_nodes_k3.csv").sort_values("betweenness", ascending=False)
    source = quality["source_records"]
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Reported AI incidents from OECD AIM, AIID and the MIT AI Incident Tracker mapped to HEART AI Risk Taxonomy cards.">
<title>AI risk incidents | HEART</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/styles-v2.css"><link rel="stylesheet" href="assets/institution.css"><link rel="stylesheet" href="assets/explorer-layout.css?v=shared-shell-20261010"><link rel="stylesheet" href="assets/incidents.css?v=20261021"></head>
<body><header class="site-header"><a class="brand" href="./" aria-label="HEART home"><span class="heart-brand-copy"><span class="brand-kicker"><span class="brand-gold-dot" aria-hidden="true"></span>AI Risk Taxonomy for General, Agentic, and Physical AI</span><strong>HEA<span class="heart-brand-r">R</span>T</strong><small>Hybrid Evidence-based AI Risk Taxonomy</small></span></a><nav aria-label="Primary navigation"><a href="https://github.com/deep1003/HEART-AI-Risk-Taxonomy" target="_blank" rel="noopener noreferrer">GitHub</a></nav></header>
<main><nav class="section-nav" aria-label="Page sections"><div class="explorer-tabs"><a href="about.html?v=shared-shell-20261010">About HEART</a><a href="./?v=shared-shell-20261010#explore">AI risk taxonomy</a><a href="./?v=shared-shell-20261010#ai-risk-space">AI risk space</a><a href="incidents.html?v=20261021" aria-current="page">AI risk incidents</a></div></nav>
<article class="incident-report"><p class="eyebrow">HEART incident evidence · 21 October 2026</p><h1>Reported AI incidents concentrate around a connected core of recurring risks</h1><p class="lead">OECD AIM, AIID and the MIT AI Incident Tracker were normalized at source-record level, linked without double-counting MIT's AIID-derived records, and mapped to HEART L4 risk cards. The results describe public reporting and model-based semantic correspondence—not incident prevalence, causal frequency, or risk severity.</p>
<section class="metric-grid"><div><strong>{source['OECD AIM actual incidents']:,}</strong><span>OECD AIM incidents</span></div><div><strong>{source['AIID incidents']:,}</strong><span>AIID incidents</span></div><div><strong>{source['MIT Tracker derived classifications']:,}</strong><span>MIT derived classifications</span></div><div><strong>{quality['canonical_incidents']:,}</strong><span>canonical analysis records</span></div></section>
<section><h2>Source harmonization</h2><p>The public release keeps one row per source record and a separate canonical event table. OECD AIM rows carrying an AIID ID are linked to AIID; MIT Tracker records are treated as AIID enrichments rather than new events. Two additional title/date matches are retained only as review candidates and are not merged.</p>
<div class="table-wrap"><table><thead><tr><th>Source</th><th>Role</th><th>Snapshot</th><th>Severity treatment</th></tr></thead><tbody><tr><td>OECD AI Incidents Monitor</td><td>Incident and hazard monitor; this analysis retains only records labelled “AI incident”</td><td>2026-08-24</td><td>Not available in the local snapshot; no imputation</td></tr><tr><td>AI Incident Database</td><td>Canonical incident identity and report linkage</td><td>2026-10-19</td><td>CSET where published; MIT enrichment where linked</td></tr><tr><td>MIT AI Incident Tracker</td><td>AIID-derived risk, cause, harm and 1–5 severity classification</td><td>2026-10-21</td><td>Model-generated classification; not systematically human validated</td></tr></tbody></table></div></section>
<section><h2>A bipartite view reveals repeatedly activated HEART cards</h2><p class="chart-subtitle">Each line links one reported incident to one of its three closest HEART cards; the displayed network is filtered for legibility, while all {quality['canonical_incidents']:,} incidents are included in downloadable metrics.</p><figure><img src="assets/incident-figures/bipartite-network-k3.svg" alt="Filtered bipartite network connecting incident nodes to HEART L4 risk-card nodes"><figcaption><strong>Notes:</strong> The view contains 140 incidents with the most displayed connections to the 35 most frequent k=3 cards. Filtering changes the picture, not the underlying calculations. Card assignment uses BGE-M3 cosine similarity and has not been human validated. <a href="data/incidents/downloads/incident_heart_edges_k5.csv.gz">Data</a></figcaption></figure></section>
<section><h2>Risk co-occurrence is connected yet divided into interpretable communities</h2><p class="chart-subtitle">A tie joins two HEART cards when both fall within the same incident's top-three mappings; larger nodes recur across more incidents and stronger ties combine normalized association with repeated co-occurrence.</p><figure><img src="assets/incident-figures/risk-cooccurrence-network-k3.svg" alt="Network of HEART risks that co-occur in incident mappings"><figcaption><strong>Notes:</strong> The figure shows the 55 highest-PageRank cards and 180 strongest displayed ties. The full k=3 graph contains {k3['risk_nodes']:,} nodes and {k3['cooccurrence_edges']:,} edges. Co-occurrence is semantic co-mapping, not proof of a causal relationship. <a href="data/incidents/downloads/risk_cooccurrence_edges_k3.csv">Data</a></figcaption></figure></section>
<section><h2>A small minority of cards connects much of the reported-incident space</h2><p class="chart-subtitle">Degree counts distinct co-occurring HEART cards; right-shifted points connect to more kinds of risk, while upper points show how many cards have that degree.</p><figure><img src="assets/incident-figures/degree-distribution.svg" alt="Log-log degree distributions for k equals 3 and k equals 5 networks"><figcaption><strong>Notes:</strong> k=3 is the primary specification and k=5 is a sensitivity analysis. Both networks are connected; adding two mappings per incident raises density from {fmt(k3['density'])} to {fmt(k5['density'])} and lowers modularity from {fmt(k3['modularity'])} to {fmt(k5['modularity'])}. <a href="data/incidents/downloads/network_metrics.json">Data</a></figcaption></figure></section>
<section><h2>Network structure and hubs</h2><div class="metric-grid compact"><div><strong>{k3['communities']}</strong><span>Louvain communities, k=3</span></div><div><strong>{fmt(k3['modularity'])}</strong><span>modularity</span></div><div><strong>{fmt(k3['average_clustering_weighted'])}</strong><span>weighted clustering</span></div><div><strong>{fmt(k3['degree_assortativity'])}</strong><span>degree assortativity</span></div></div>
<h3>Most frequently activated cards</h3><div class="table-wrap"><table><thead><tr><th>HEART ID</th><th>Risk card</th><th>Incidents</th><th>PageRank</th><th>Betweenness</th></tr></thead><tbody>{table_rows(nodes)}</tbody></table></div>
<h3>Bridge cards by betweenness</h3><div class="table-wrap"><table><thead><tr><th>HEART ID</th><th>Risk card</th><th>Incidents</th><th>PageRank</th><th>Betweenness</th></tr></thead><tbody>{table_rows(bridges)}</tbody></table></div>
<p>The incident-frequency hubs are dominated by deepfakes, surveillance, political manipulation, sexualised imagery and fraud. The strongest bridge is automated-driving control-transfer failure, which links physical-safety incidents to otherwise separate general and agentic-risk neighborhoods. Hub status partly reflects what public databases report and what HEART distinguishes into separate cards.</p></section>
<section><h2>Methods, provenance and limitations</h2><ol><li><strong>Occurrence filter:</strong> OECD AIM hazards were excluded; AIID incidents and near-harms were retained because the source does not expose a complete event-level near-miss flag.</li><li><strong>Deduplication:</strong> exact AIID identifiers determine merges. Normalized titles, dates, entities and fingerprints remain available for future review; fuzzy candidates are never merged automatically.</li><li><strong>Mapping:</strong> incident title, description, source risk label, harm type and AI-system fields were embedded with the same BGE-M3 model used for HEART. Each record receives top-5 cards with explicit k=3 and k=5 flags.</li><li><strong>Networks:</strong> the bipartite graph uses incident–card edges. The projected risk network connects cards co-mapped to an incident; raw count, Jaccard and association strength are all released.</li></ol><p><strong>Limitations:</strong> source coverage is selective and news-driven; MIT classifications are produced by an LLM pipeline and are not systematically validated; severity is unavailable for most OECD AIM rows; top-k mapping forces a fixed number of links even for ambiguous records; 92% of k=3 edges fall in General AI, reflecting both corpus composition and taxonomy granularity. Results therefore support pattern discovery, not prevalence, incidence-rate, or causal claims.</p></section>
<section><h2>Download the reproducible data</h2><ul class="downloads"><li><a href="data/incidents/downloads/source_records.csv.gz">Normalized source records</a></li><li><a href="data/incidents/downloads/canonical_incidents_compact.json">Canonical analysis incidents (compact)</a></li><li><a href="data/incidents/downloads/incident_heart_edges_k5.csv.gz">Incident–HEART mappings (k3 and k5)</a></li><li><a href="data/incidents/downloads/duplicate_candidates.csv">Duplicate-review candidates</a></li><li><a href="data/incidents/downloads/risk_network_nodes_k3.csv">Risk-node metrics</a></li><li><a href="data/incidents/downloads/risk_cooccurrence_edges_k3.csv">Risk co-occurrence edges</a></li><li><a href="data/incidents/downloads/network_metrics.json">Graph-level metrics</a></li></ul><p class="source-note"><strong>Sources:</strong> <a href="https://oecd.ai/en/incidents" target="_blank" rel="noopener">OECD AI Incidents Monitor</a>; <a href="https://incidentdatabase.ai/research/snapshots/" target="_blank" rel="noopener">AIID sanctioned snapshots</a>; <a href="https://airisk.mit.edu/ai-incident-tracker" target="_blank" rel="noopener">MIT AI Incident Tracker</a>. Snapshot and field-level provenance are retained in the downloads.</p></section>
</article></main><footer class="site-footer publisher-footer"><div class="publisher-identity"><a class="kt-logo-link" href="https://corp.kt.com/eng/" target="_blank" rel="noopener noreferrer" aria-label="KT Corporation official website"><img src="assets/kt-logo-light.svg" alt="KT" width="40" height="40"></a><div><p class="publisher-name">Frontier AI Lab, KT Corporation</p><a class="publisher-contact" href="mailto:responsible.ai@kt.com">responsible.ai@kt.com</a></div></div></footer></body></html>'''
    (ROOT / "incidents.html").write_text(page, encoding="utf-8")


def main() -> None:
    bipartite_figure()
    cooccurrence_figure()
    degree_figure()
    build_downloads()
    build_page()
    print("built incident figures, downloads, and incidents.html")


if __name__ == "__main__":
    main()
