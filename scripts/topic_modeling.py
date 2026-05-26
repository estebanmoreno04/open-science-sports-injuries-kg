#!/usr/bin/env python3
"""
topic_modeling.py
-----------------
Topic modeling pipeline for the Sports Injuries KG.

Reads abstracts from data/metadata/papers.csv, runs BERTopic (default) or LDA,
and writes two outputs:
  - data/processed/topics.csv            → consumed by src/build_rdf.py
  - results/topics/topics_summary.csv    → human-readable topic descriptions

The output format matches what build_rdf.py expects:
  paper_id, topic_id, topic_label, top_terms, confidence_score, threshold, model_used

Usage:
    python scripts/topic_modeling.py
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

log = logging.getLogger("topic-modeling")

# ── Project root: one level up from scripts/ ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Configuration (edit these instead of CLI args) ───────────────────────────
INPUT_CSV       = PROJECT_ROOT / "data" / "metadata" / "papers.csv"
OUTPUT_CSV      = PROJECT_ROOT / "data" / "processed" / "topics.csv"
SUMMARY_DIR     = PROJECT_ROOT / "results" / "topics"

METHODS         = ["bertopic", "lda"]  # runs both; remove one to skip it
NUM_TOPICS      = 5                    # only used for lda
TOPIC_THRESHOLD = 0.4
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CSV_SEP         = ";"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_papers(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=CSV_SEP, dtype=str)
    df["paper_id"] = df["paper_id"].str.strip()
    df["abstract"] = df["abstract"].str.strip()
    n_raw = len(df)
    df = df[df["abstract"].notna() & (df["abstract"] != "")]
    df = df.drop_duplicates(subset="paper_id", keep="first").reset_index(drop=True)
    log.info("Loaded %d papers (%d with valid abstract)", n_raw, len(df))
    return df


# ── BERTopic ─────────────────────────────────────────────────────────────────

def run_bertopic(abstracts: list[str], embeddings: np.ndarray,
                 threshold: float) -> tuple[list[dict], list[dict]]:
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN

    n = len(abstracts)
    umap_model = UMAP(
        n_neighbors=min(5, n - 1), n_components=min(5, n - 1),
        min_dist=0.0, metric="cosine", random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=max(2, n // 10), min_samples=1,
        metric="euclidean", prediction_data=True,
    )
    model = BERTopic(
        umap_model=umap_model, hdbscan_model=hdbscan_model,
        calculate_probabilities=True, verbose=True,
    )

    topics, probs = model.fit_transform(abstracts, embeddings)

    summaries = []
    for _, row in model.get_topic_info().iterrows():
        tid = row["Topic"]
        if tid == -1:
            summaries.append({"topic_id": "T_outlier", "label": "Outliers", "terms": ""})
        else:
            words = model.get_topic(tid)
            summaries.append({
                "topic_id": f"T{tid:02d}",
                "label": f"Topic_{tid}",
                "terms": ", ".join(w for w, _ in words[:10]),
            })

    assignments = []
    for i in range(len(abstracts)):
        row_probs = probs[i]
        if row_probs.ndim == 0:
            row_probs = np.array([float(row_probs)])
        for tid_idx, prob in enumerate(row_probs):
            if prob >= threshold:
                assignments.append({"doc_idx": i, "topic_id": f"T{tid_idx:02d}",
                                    "score": round(float(prob), 4)})
        # Hard assignment (including outliers)
        hard = topics[i]
        hard_id = "T_outlier" if hard == -1 else f"T{hard:02d}"
        if not any(a["doc_idx"] == i and a["topic_id"] == hard_id for a in assignments):
            best_score = float(probs[i].max()) if probs[i].ndim else float(probs[i])
            assignments.append({"doc_idx": i, "topic_id": hard_id,
                                "score": round(best_score, 4)})

    return summaries, assignments


# ── LDA ──────────────────────────────────────────────────────────────────────

def run_lda(abstracts: list[str], num_topics: int,
            threshold: float) -> tuple[list[dict], list[dict]]:
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer

    vec = CountVectorizer(max_df=0.90, min_df=2, stop_words="english",
                          max_features=2000)
    dtm = vec.fit_transform(abstracts)
    features = vec.get_feature_names_out()

    lda = LatentDirichletAllocation(
        n_components=num_topics, max_iter=30,
        learning_method="online", random_state=42,
    )
    doc_topic = lda.fit_transform(dtm)

    summaries = []
    for tid in range(num_topics):
        top_idx = lda.components_[tid].argsort()[-10:][::-1]
        summaries.append({
            "topic_id": f"T{tid:02d}",
            "label": f"Topic_{tid}",
            "terms": ", ".join(features[i] for i in top_idx),
        })

    assignments = []
    for i in range(len(abstracts)):
        for tid in range(num_topics):
            prob = float(doc_topic[i, tid])
            if prob >= threshold:
                assignments.append({"doc_idx": i, "topic_id": f"T{tid:02d}",
                                    "score": round(prob, 4)})

    return summaries, assignments


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    log.info("Project root: %s", PROJECT_ROOT)

    if not INPUT_CSV.exists():
        log.error("Input CSV not found: %s", INPUT_CSV)
        sys.exit(1)

    df = load_papers(INPUT_CSV)
    abstracts = df["abstract"].tolist()
    paper_ids = df["paper_id"].tolist()

    # Pre-compute embeddings once (shared by bertopic and similarity)
    embeddings = None
    if "bertopic" in METHODS:
        log.info("Computing embeddings with %s ...", EMBEDDING_MODEL)
        model = SentenceTransformer(EMBEDDING_MODEL)
        embeddings = model.encode(abstracts, show_progress_bar=True,
                                  normalize_embeddings=True, convert_to_numpy=True)

    for method in METHODS:
        log.info("=" * 50)
        log.info("Running %s ...", method)

        if method == "bertopic":
            summaries, assignments = run_bertopic(abstracts, embeddings, TOPIC_THRESHOLD)
            method_label = f"BERTopic ({EMBEDDING_MODEL})"
        elif method == "lda":
            summaries, assignments = run_lda(abstracts, NUM_TOPICS, TOPIC_THRESHOLD)
            method_label = f"LDA (sklearn, K={NUM_TOPICS})"
        else:
            log.warning("Unknown method: %s — skipping", method)
            continue

        # Build topics CSV in build_rdf format
        summary_map = {s["topic_id"]: s for s in summaries}
        rows = []
        for a in assignments:
            tid = a["topic_id"]
            info = summary_map.get(tid, {})
            rows.append({
                "paper_id": paper_ids[a["doc_idx"]],
                "topic_id": tid,
                "topic_label": info.get("label", tid),
                "top_terms": info.get("terms", ""),
                "confidence_score": a["score"],
                "threshold": TOPIC_THRESHOLD,
                "model_used": method_label,
            })

        out_df = pd.DataFrame(rows)

        # Per-method output files
        out_path = OUTPUT_CSV.parent / f"topics_{method}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_path, index=False)
        log.info("Wrote %d topic assignments to %s", len(out_df), out_path)

        SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
        summary_df = pd.DataFrame(summaries)
        summary_df.to_csv(SUMMARY_DIR / f"topics_summary_{method}.csv", index=False)
        log.info("Wrote topic summaries to %s", SUMMARY_DIR / f"topics_summary_{method}.csv")

    # Also write a default topics.csv (last method run) for build_rdf.py
    if rows:
        out_df.to_csv(OUTPUT_CSV, index=False)
        log.info("Default topics.csv → %s (from %s)", OUTPUT_CSV, method)

    log.info("Done.")


if __name__ == "__main__":
    main()