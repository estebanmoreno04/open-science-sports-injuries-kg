#!/usr/bin/env python3
"""
Preprocess an RDF/Turtle Knowledge Graph for the Cytoscape.js explorer.

Reads the .ttl file, computes sentence embeddings, runs topic modeling
(BERTopic or LDA), calculates pairwise cosine similarity, and writes
a single JSON file that kg_explorer.html can load.

Usage:
    python prepare_kg_demo.py --ttl sports_injuries_kg.ttl
    python prepare_kg_demo.py --ttl sports_injuries_kg.ttl --method lda --num-topics 5
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
from rdflib import Graph, Namespace, RDF
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger("prepare-kg-demo")

SIO = Namespace("http://kg.sports-injuries.org/ontology/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.75
TOPIC_THRESHOLD = 0.4

# ── RDF parsing ──────────────────────────────────────────────────────────────

def parse_ttl(ttl_path: Path) -> list[dict]:
    """Extract paper metadata from the Turtle file."""
    g = Graph()
    g.parse(str(ttl_path), format="turtle")

    papers = []
    for subj in g.subjects(RDF.type, SIO.Paper):
        uri = str(subj)
        paper = {"uri": uri}

        prop_map = {
            SIO.paperId:         "paperId",
            SIO.title:           "title",
            SIO.abstractText:    "abstract",
            SIO.doi:             "doi",
            SIO.publicationYear: "year",
        }
        for prop, key in prop_map.items():
            vals = list(g.objects(subj, prop))
            if vals:
                v = vals[0]
                paper[key] = int(v) if key == "year" else str(v)

        same_as = list(g.objects(subj, OWL.sameAs))
        if same_as:
            paper["sameAs"] = str(same_as[0])

        papers.append(paper)

    papers.sort(key=lambda p: p.get("paperId", ""))
    return papers


# ── Embeddings ───────────────────────────────────────────────────────────────

def compute_embeddings(texts: list[str]) -> np.ndarray:
    model = SentenceTransformer(EMBEDDING_MODEL)
    return model.encode(texts, show_progress_bar=True, convert_to_numpy=True)


# ── Topic modeling ───────────────────────────────────────────────────────────

def run_bertopic(abstracts: list[str], embeddings: np.ndarray,
                 threshold: float) -> tuple[list[dict], list[dict]]:
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN

    n = len(abstracts)
    umap_model = UMAP(n_neighbors=min(5, n - 1), n_components=min(5, n - 1),
                      min_dist=0.0, metric="cosine", random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=max(2, n // 10), min_samples=1,
                            metric="euclidean", prediction_data=True)

    model = BERTopic(umap_model=umap_model, hdbscan_model=hdbscan_model,
                     calculate_probabilities=True, verbose=True)
    topics, probs = model.fit_transform(abstracts, embeddings)

    # Topic summaries
    topic_summaries = []
    for _, row in model.get_topic_info().iterrows():
        tid = row["Topic"]
        if tid == -1:
            topic_summaries.append({"id": -1, "name": "Outliers", "terms": ""})
        else:
            words = model.get_topic(tid)
            topic_summaries.append({
                "id": tid,
                "name": f"Topic_{tid}",
                "terms": ", ".join(w for w, _ in words[:10]),
            })

    # Assignments
    assignments = []
    for i in range(len(abstracts)):
        row_probs = probs[i]
        if row_probs.ndim == 0:
            row_probs = np.array([float(row_probs)])
        for tid_idx, prob in enumerate(row_probs):
            if prob >= threshold:
                assignments.append({"paper_idx": i, "topic_id": tid_idx,
                                    "score": round(float(prob), 4)})
        # Also record hard assignment (including outlier -1)
        hard = topics[i]
        if not any(a["paper_idx"] == i and a["topic_id"] == hard for a in assignments):
            assignments.append({"paper_idx": i, "topic_id": hard,
                                "score": round(float(probs[i].max()) if probs[i].ndim else float(probs[i]), 4)})

    return topic_summaries, assignments


def run_lda(abstracts: list[str], num_topics: int,
            threshold: float) -> tuple[list[dict], list[dict]]:
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer

    vec = CountVectorizer(max_df=0.90, min_df=2, stop_words="english", max_features=2000)
    dtm = vec.fit_transform(abstracts)
    features = vec.get_feature_names_out()

    lda = LatentDirichletAllocation(n_components=num_topics, max_iter=30,
                                   learning_method="online", random_state=42)
    doc_topic = lda.fit_transform(dtm)

    topic_summaries = []
    for tid in range(num_topics):
        top_idx = lda.components_[tid].argsort()[-10:][::-1]
        topic_summaries.append({
            "id": tid,
            "name": f"Topic_{tid}",
            "terms": ", ".join(features[i] for i in top_idx),
        })

    assignments = []
    for i in range(len(abstracts)):
        for tid in range(num_topics):
            prob = float(doc_topic[i, tid])
            if prob >= threshold:
                assignments.append({"paper_idx": i, "topic_id": tid,
                                    "score": round(prob, 4)})

    return topic_summaries, assignments


# ── Similarity ───────────────────────────────────────────────────────────────

def compute_similarities(embeddings: np.ndarray,
                         threshold: float) -> tuple[list[dict], np.ndarray]:
    sim_matrix = cosine_similarity(embeddings)
    n = len(embeddings)
    links = []
    for i, j in combinations(range(n), 2):
        score = float(sim_matrix[i, j])
        if score >= threshold:
            links.append({"source_idx": i, "target_idx": j,
                          "score": round(score, 4)})
    return links, sim_matrix


# ── Build Cytoscape JSON ────────────────────────────────────────────────────

def build_cytoscape_json(papers: list[dict], topic_summaries: list[dict],
                         assignments: list[dict], sim_links: list[dict],
                         sim_matrix: np.ndarray, method: str) -> dict:
    """Build the full JSON payload for the explorer."""

    # Map paper_idx → primary topic (highest score)
    primary_topic: dict[int, int] = {}
    for a in assignments:
        idx = a["paper_idx"]
        if idx not in primary_topic or a["score"] > primary_topic[idx]:
            primary_topic[idx] = a["topic_id"]

    # Nodes
    nodes = []
    for i, p in enumerate(papers):
        node_data = {
            "id": p.get("paperId", f"P{i+1:02d}"),
            "label": p.get("paperId", f"P{i+1:02d}"),
            "title": p.get("title", ""),
            "year": p.get("year", ""),
            "doi": p.get("doi", ""),
            "abstract": p.get("abstract", "")[:300] + ("..." if len(p.get("abstract", "")) > 300 else ""),
            "fullAbstract": p.get("abstract", ""),
            "sameAs": p.get("sameAs", ""),
            "type": "Paper",
            "topicId": primary_topic.get(i, -1),
        }
        nodes.append({"data": node_data})

    # Edges (similarity links above threshold)
    edges = []
    for sl in sim_links:
        src = papers[sl["source_idx"]].get("paperId", f"P{sl['source_idx']+1:02d}")
        tgt = papers[sl["target_idx"]].get("paperId", f"P{sl['target_idx']+1:02d}")
        edges.append({
            "data": {
                "id": f"sim_{src}_{tgt}",
                "source": src,
                "target": tgt,
                "score": sl["score"],
                "type": "SimilarityLink",
            }
        })

    # Full similarity matrix (for the similarity dropdown — all pairs, not just above threshold)
    id_list = [p.get("paperId", f"P{i+1:02d}") for i, p in enumerate(papers)]
    full_sim = {}
    for i in range(len(papers)):
        row = {}
        for j in range(len(papers)):
            if i != j:
                row[id_list[j]] = round(float(sim_matrix[i, j]), 4)
        full_sim[id_list[i]] = row

    return {
        "metadata": {
            "generated": date.today().isoformat(),
            "embeddingModel": EMBEDDING_MODEL,
            "topicMethod": method,
            "similarityThreshold": SIMILARITY_THRESHOLD,
            "topicThreshold": TOPIC_THRESHOLD,
            "numPapers": len(papers),
        },
        "elements": {"nodes": nodes, "edges": edges},
        "topics": topic_summaries,
        "topicAssignments": assignments,
        "similarityMatrix": full_sim,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(description="Prepare KG data for the Cytoscape explorer")
    p.add_argument("--ttl", type=Path, required=True, help="Input Turtle file")
    p.add_argument("--out", type=Path, default=Path("graph_data.json"), help="Output JSON")
    p.add_argument("--method", choices=["bertopic", "lda"], default="bertopic")
    p.add_argument("--num-topics", type=int, default=5, help="Number of topics (LDA only)")
    p.add_argument("--sim-threshold", type=float, default=SIMILARITY_THRESHOLD)
    p.add_argument("--topic-threshold", type=float, default=TOPIC_THRESHOLD)
    args = p.parse_args()

    # global SIMILARITY_THRESHOLD, TOPIC_THRESHOLD
    SIMILARITY_THRESHOLD = args.sim_threshold
    TOPIC_THRESHOLD = args.topic_threshold

    log.info("Parsing %s ...", args.ttl)
    papers = parse_ttl(args.ttl)
    log.info("Found %d papers", len(papers))

    abstracts = [p.get("abstract", "") for p in papers]
    valid = [bool(a.strip()) for a in abstracts]
    valid_abstracts = [a for a, v in zip(abstracts, valid) if v]
    valid_indices = [i for i, v in enumerate(valid) if v]

    log.info("%d papers have abstracts", len(valid_abstracts))

    # Embeddings
    log.info("Computing embeddings ...")
    embeddings = compute_embeddings(valid_abstracts)

    # Topics
    log.info("Running %s ...", args.method)
    if args.method == "bertopic":
        topic_summaries, raw_assignments = run_bertopic(
            valid_abstracts, embeddings, args.topic_threshold)
    else:
        topic_summaries, raw_assignments = run_lda(
            valid_abstracts, args.num_topics, args.topic_threshold)

    # Remap paper_idx back to global index
    assignments = []
    for a in raw_assignments:
        assignments.append({**a, "paper_idx": valid_indices[a["paper_idx"]]})

    # Similarity
    log.info("Computing similarities ...")
    # Build full matrix for all papers (zeros for those without abstracts)
    full_embeddings = np.zeros((len(papers), embeddings.shape[1]))
    for local_i, global_i in enumerate(valid_indices):
        full_embeddings[global_i] = embeddings[local_i]

    sim_links, sim_matrix = compute_similarities(full_embeddings, args.sim_threshold)

    # Build output
    data = build_cytoscape_json(papers, topic_summaries, assignments,
                                sim_links, sim_matrix, args.method)

    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Wrote %s (%d nodes, %d edges)", args.out, len(data["elements"]["nodes"]),
             len(data["elements"]["edges"]))


if __name__ == "__main__":
    main()
