from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template
from rdflib import Graph as RDFGraph, Namespace, RDF

log = logging.getLogger("kg-explorer")

ONT = Namespace("http://kg.sports-injuries.org/ontology/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

PROJECT_ROOT = Path(__file__).resolve().parent

KG_TTL     = PROJECT_ROOT / "kg" / "sports_injuries_kg.ttl"
SIM_DIR    = PROJECT_ROOT / "results" / "similarity"
TOPICS_DIR = PROJECT_ROOT / "data" / "processed"

# Topic model files
TOPIC_MODELS = {
    "bertopic": TOPICS_DIR / "topics_bertopic.csv",
    "lda":      TOPICS_DIR / "topics_lda.csv",
}
TOPICS_CSV_FALLBACK = TOPICS_DIR / "topics.csv"

# Similarity matrix files — both models the project already computed
SIM_MODELS = {
    "all-MiniLM-L6-v2": {
        "matrix": SIM_DIR / "similarity_matrix_sentence_transformers_all_MiniLM_L6_v2.csv",
        "label": "all-MiniLM-L6-v2 (sentence-transformers)",
    },
    "e5-small-v2": {
        "matrix": SIM_DIR / "similarity_matrix_intfloat_e5_small_v2.csv",
        "label": "e5-small-v2 (intfloat)",
    },
}

SIMILARITY_THRESHOLD = 0.60

# Flask app
app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)


# RDF parsing
def parse_ttl(path: Path) -> list[dict]:
    """Extract paper metadata from the Turtle KG."""
    g = RDFGraph()
    g.parse(str(path), format="turtle")

    papers = []
    for subj in g.subjects(RDF.type, ONT.Paper):
        uri = str(subj)
        paper = {"uri": uri}

        prop_map = {
            ONT.paperId:         "paperId",
            ONT.title:           "title",
            ONT.abstractText:    "abstract",
            ONT.doi:             "doi",
            ONT.publicationYear: "year",
        }

        for prop, key in prop_map.items():
            vals = list(g.objects(subj, prop))
            if vals:
                v = vals[0]
                paper[key] = int(v) if key == "year" else str(v)

        same_as = list(g.objects(subj, OWL.sameAs))
        if same_as:
            paper["sameAs"] = str(same_as[0])

        # NER / acknowledged entities
        acknowledged_entities = []
        for entity in g.objects(subj, ONT.acknowledges):
            entity_types = [str(t).split("/")[-1] for t in g.objects(entity, RDF.type)]
            entity_names = list(g.objects(entity, ONT.name))

            entity_label = str(entity_names[0]) if entity_names else str(entity).split("/")[-1]
            entity_label = entity_label.strip()

            # Basic filter to avoid obvious extraction noise from section headers.
            if entity_label.upper() in {"ACKNOWLED", "ACKNOWLEDGEMENT", "ACKNOWLEDGEMENTS"}:
                continue

            acknowledged_entities.append({
                "name": entity_label,
                "type": entity_types[0] if entity_types else "ExtractedEntity",
                "uri": str(entity),
            })

        paper["acknowledgedEntities"] = acknowledged_entities

        papers.append(paper)

    papers.sort(key=lambda p: p.get("paperId", ""))
    return papers


# Similarity matrices
def load_similarity_matrices() -> dict[str, dict[str, dict[str, float]]]:
    """Load pre-computed similarity matrices (one per model)."""
    result = {}

    for model_key, info in SIM_MODELS.items():
        path = info["matrix"]

        if not path.exists():
            log.warning("Similarity matrix not found: %s", path)
            continue

        df = pd.read_csv(path, index_col=0)

        matrix = {}
        for paper_id in df.index:
            row = {}
            for other_id in df.columns:
                if paper_id != other_id:
                    row[other_id] = round(float(df.loc[paper_id, other_id]), 4)
            matrix[paper_id] = row

        result[model_key] = matrix
        log.info("Loaded similarity matrix: %s (%d papers)", model_key, len(df))

    return result


# Topics
def _parse_topic_csv(path: Path) -> tuple[list[dict], dict[str, int]]:
    """Parse a single topics CSV. Returns (summaries, paper→primary_topic map)."""
    # Try semicolon first (project convention), fall back to comma
    try:
        df = pd.read_csv(path, sep=";")
        if len(df.columns) <= 1:
            df = pd.read_csv(path)
    except Exception:
        df = pd.read_csv(path)

    topic_groups = df.groupby("topic_id").first().reset_index()

    summaries = []
    for _, row in topic_groups.iterrows():
        tid_str = str(row["topic_id"])

        try:
            numeric_id = int(tid_str.replace("T", "").replace("_outlier", "-1"))
        except ValueError:
            numeric_id = -1

        summaries.append({
            "id": numeric_id,
            "name": str(row.get("topic_label", tid_str)),
            "terms": str(row.get("top_terms", "")),
        })

    primary = {}
    for _, row in df.iterrows():
        pid = str(row["paper_id"])
        tid_str = str(row["topic_id"])

        try:
            numeric_id = int(tid_str.replace("T", "").replace("_outlier", "-1"))
        except ValueError:
            numeric_id = -1

        score = float(row.get("confidence_score", 0))

        if pid not in primary or score > primary[pid][1]:
            primary[pid] = (numeric_id, score)

    primary_map = {pid: tid for pid, (tid, _) in primary.items()}
    return summaries, primary_map


def load_all_topics() -> dict[str, tuple[list[dict], dict[str, int]]]:
    """Load topic assignments for every available method.
    Returns {method_name: (summaries, primary_map)}.
    """
    result = {}

    for method, path in TOPIC_MODELS.items():
        if path.exists():
            summaries, primary = _parse_topic_csv(path)
            result[method] = (summaries, primary)
            log.info("Loaded topics [%s]: %s (%d summaries)", method, path, len(summaries))

    if not result and TOPICS_CSV_FALLBACK.exists():
        summaries, primary = _parse_topic_csv(TOPICS_CSV_FALLBACK)
        result["default"] = (summaries, primary)
        log.info("Loaded fallback topics from %s", TOPICS_CSV_FALLBACK)

    if not result:
        log.warning("No topic files found — topics disabled")

    return result


# Build Cytoscape payload
def build_graph_data(papers, sim_matrices, all_topics):
    default_model = "all-MiniLM-L6-v2"
    default_matrix = sim_matrices.get(default_model, {})

    # Pick the first available topic method as default for node topicId
    available_topic_methods = list(all_topics.keys())
    default_topic_method = available_topic_methods[0] if available_topic_methods else None
    default_primary = all_topics[default_topic_method][1] if default_topic_method else {}

    nodes = []
    for p in papers:
        pid = p.get("paperId", "")
        abstract = p.get("abstract", "")

        nodes.append({"data": {
            "id": pid,
            "label": pid,
            "title": p.get("title", ""),
            "year": p.get("year", ""),
            "doi": p.get("doi", ""),
            "abstract": abstract[:300] + ("..." if len(abstract) > 300 else ""),
            "fullAbstract": abstract,
            "sameAs": p.get("sameAs", ""),
            "acknowledgedEntities": p.get("acknowledgedEntities", []),
            "type": "Paper",
            "topicId": default_primary.get(pid, -1),
        }})

    edges = []
    seen = set()

    for src, row in default_matrix.items():
        for tgt, score in row.items():
            pair = tuple(sorted([src, tgt]))

            if pair in seen:
                continue

            seen.add(pair)

            if score >= SIMILARITY_THRESHOLD:
                edges.append({"data": {
                    "id": f"sim_{src}_{tgt}",
                    "source": src,
                    "target": tgt,
                    "score": score,
                    "type": "SimilarityLink",
                }})

    # Build per-method topic data for the frontend toggle
    topic_models = {}

    for method, (summaries, primary_map) in all_topics.items():
        topic_models[method] = {
            "summaries": summaries,
            "primaryTopics": {pid: tid for pid, tid in primary_map.items()},
        }

    return {
        "metadata": {
            "similarityThreshold": SIMILARITY_THRESHOLD,
            "availableModels": list(sim_matrices.keys()),
            "defaultModel": default_model,
            "availableTopicMethods": available_topic_methods,
            "defaultTopicMethod": default_topic_method,
            "numPapers": len(papers),
        },
        "elements": {"nodes": nodes, "edges": edges},
        "topicModels": topic_models,
        "similarityMatrices": sim_matrices,
    }


# Global payload (loaded once)
GRAPH_PAYLOAD: dict = {}


def init_data():
    global GRAPH_PAYLOAD

    # Validate required files
    if not KG_TTL.exists():
        log.error("KG file not found: %s", KG_TTL)
        log.error("Make sure you run app.py from the project root.")
        sys.exit(1)

    if not SIM_DIR.exists():
        log.error("Similarity results not found: %s", SIM_DIR)
        sys.exit(1)

    log.info("Loading KG from %s ...", KG_TTL)
    papers = parse_ttl(KG_TTL)
    log.info("Parsed %d papers", len(papers))

    sim_matrices = load_similarity_matrices()
    if not sim_matrices:
        log.error("No similarity matrices found in %s", SIM_DIR)
        sys.exit(1)

    all_topics = load_all_topics()

    GRAPH_PAYLOAD = build_graph_data(papers, sim_matrices, all_topics)
    log.info(
        "Graph payload ready: %d nodes, %d edges, topic methods: %s",
        len(GRAPH_PAYLOAD["elements"]["nodes"]),
        len(GRAPH_PAYLOAD["elements"]["edges"]),
        list(all_topics.keys()),
    )


# Routes
@app.route("/")
def index():
    return render_template("kg_explorer.html")


@app.route("/api/graph_data")
def graph_data():
    return jsonify(GRAPH_PAYLOAD)


# Main
def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(description="Sports Injuries KG Explorer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()

    init_data()

    print(f"\n  KG Explorer running at http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
