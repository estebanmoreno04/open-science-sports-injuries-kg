"""
ner_acknowledgements.py
=======================
Applies Named Entity Recognition (NER) to the acknowledgements text
extracted from papers to identify:
  - PERSON: collaborators, researchers mentioned
  - ORGANIZATION: funding bodies, institutions
  - PROJECT: grant IDs and award numbers
 
Model used: dslim/bert-base-NER (HuggingFace)
  - Fine-tuned on CoNLL-2003 for general NER
  - Recognises PER, ORG, LOC, MISC entities
  - Chosen over biomedical models because acknowledgements contain
    general named entities (people, orgs, grant IDs), not clinical terms
 
Grant ID detection: regex-based post-processing
  - NER models do not reliably detect grant IDs (alphanumeric codes)
  - Regex patterns cover common formats: NIH (R01, K99), NSF, DOD, EU
 
Input:  data/processed/acknowledgements.csv
Output: data/processed/ner_entities.csv
 
Columns:
    paper_id | entity_text | entity_type | normalized_name |
    confidence_score | model_used | source_section
 
Usage:
    pip install transformers torch
    python scripts/ner_acknowledgements.py
"""
 
import csv
import os
import re
from collections import defaultdict

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV  = os.path.join(BASE_DIR, "data/processed/acknowledgements.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "data/processed/ner_entities.csv")
 
MODEL_NAME = "dslim/bert-base-NER"
SOURCE_SECTION = "acknowledgements"

# Covers: NIH (R01, K99, U01...), NSF, DOD, EU Horizon, ERC
GRANT_PATTERNS = [
    r"\b[A-Z]{1,3}\d{2}[A-Z]{2}\d{6}[-\d]*\b",   # NIH: R01AG059874-01
    r"\b[A-Z]{1,2}\d{5,8}\b",                       # NSF: 1234567
    r"\b[A-Z]\d{3,6}[A-Z]{0,3}[-\d]*\b",            # DOD: W911NF-18-1-0027
    r"\bN\d{5}-\d{2}-\d{1}-\d{4}\b",                # ONR format
    r"\b\d{4}-\d{4,}\b",                             # EU grant: 2019-12345
    r"\bGrant\s+(?:No\.?\s*)?([A-Z0-9\-/]+)\b",     # "Grant No. ABC123"
    r"\baward\s+([A-Z0-9\-]+)\b",                    # "award N00014-21-1-2437"
]

# dslim/bert-base-NER uses B-PER, I-PER, B-ORG, I-ORG, etc.
LABEL_MAP = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "ORGANIZATION",   # Location labels sometimes catch institutions
    "MISC": None,            # Skip MISC entities
}

def load_ner_pipeline():
    """Load the NER pipeline from HuggingFace."""
    from transformers import pipeline
    print(f"  Loading model: {MODEL_NAME}...")
    nlp = pipeline(
        "ner",
        model=MODEL_NAME,
        aggregation_strategy="simple",  # merges B-/I- tokens automatically
        device=-1,  # CPU; change to 0 for GPU
    )
    print(f"  Model loaded.\n")
    return nlp
 
 
def extract_grant_ids(text: str) -> list[dict]:
    """
    Extract grant/award IDs using regex patterns.
    Returns list of dicts with entity info.
    """
    entities = []
    seen = set()
    for pattern in GRANT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Use group(1) if capture group exists, else full match
            try:
                grant_id = match.group(1).strip()
            except IndexError:
                grant_id = match.group(0).strip()
 
            # Basic filter: must have at least one digit and be >3 chars
            if len(grant_id) > 3 and any(c.isdigit() for c in grant_id):
                if grant_id not in seen:
                    seen.add(grant_id)
                    entities.append({
                        "entity_text":      grant_id,
                        "entity_type":      "PROJECT",
                        "normalized_name":  grant_id.upper(),
                        "confidence_score": 1.0,  # regex = deterministic
                        "model_used":       "regex",
                    })
    return entities
 
 
def normalize_name(text: str) -> str:
    """Normalize entity name: strip, collapse spaces, title case for persons."""
    return " ".join(text.strip().split())
 
 
def run_ner(nlp, text: str) -> list[dict]:
    """
    Run NER model on text. Returns list of entity dicts.
    Filters out entities shorter than 2 chars or with score < 0.7.
    """
    if not text or not text.strip():
        return []
 
    try:
        raw_entities = nlp(text)
    except Exception as e:
        print(f"    [NER ERROR] {e}")
        return []
 
    entities = []
    seen = set()
 
    for ent in raw_entities:
        label_short = ent["entity_group"].replace("B-", "").replace("I-", "")
        entity_type = LABEL_MAP.get(label_short)
        if entity_type is None:
            continue
 
        word = ent["word"].strip()
        score = float(ent["score"])
 
        if len(word) < 2 or score < 0.70:
            continue
 
        normalized = normalize_name(word)
        if normalized in seen:
            continue
        seen.add(normalized)
 
        entities.append({
            "entity_text":      word,
            "entity_type":      entity_type,
            "normalized_name":  normalized,
            "confidence_score": round(score, 4),
            "model_used":       MODEL_NAME,
        })
 
    return entities
 
def main():
    if not os.path.exists(INPUT_CSV):
        print(f"[ERROR] Input not found: {INPUT_CSV}")
        print("Run extract_acknowledgements.py first.")
        return
 
    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        papers = list(reader)
 
    papers_with_ack = [p for p in papers if p.get("acknowledgements", "").strip()]
    print(f"  {len(papers)} papers loaded, {len(papers_with_ack)} with acknowledgements.\n")

    nlp = load_ner_pipeline()
 
    all_rows = []
    stats = defaultdict(int)
 
    for paper in papers:
        paper_id = paper.get("paper_id", "").strip()
        ack_text = paper.get("acknowledgements", "").strip()
 
        if not ack_text:
            print(f"  [{paper_id}] No acknowledgements — skipping NER.")
            continue
 
        print(f"  [{paper_id}] Running NER ({len(ack_text)} chars)...")

        ner_entities = run_ner(nlp, ack_text)

        grant_entities = extract_grant_ids(ack_text)
 
        all_entities = ner_entities + grant_entities
        stats[paper_id] = len(all_entities)
 
        if all_entities:
            types = {}
            for e in all_entities:
                t = e["entity_type"]
                types[t] = types.get(t, 0) + 1
            summary = ", ".join(f"{v} {k}" for k, v in types.items())
            print(f"    → {len(all_entities)} entities: {summary}")
        else:
            print(f"    → No entities found.")
 
        for ent in all_entities:
            all_rows.append({
                "paper_id":          paper_id,
                "entity_text":       ent["entity_text"],
                "entity_type":       ent["entity_type"],
                "normalized_name":   ent["normalized_name"],
                "confidence_score":  ent["confidence_score"],
                "model_used":        ent["model_used"],
                "source_section":    SOURCE_SECTION,
            })
 
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "paper_id", "entity_text", "entity_type", "normalized_name",    
            "confidence_score", "model_used", "source_section"
        ],delimiter=";")
        writer.writeheader()
        writer.writerows(all_rows)
 
    total_persons = sum(1 for r in all_rows if r["entity_type"] == "PERSON")
    total_orgs    = sum(1 for r in all_rows if r["entity_type"] == "ORGANIZATION")
    total_projs   = sum(1 for r in all_rows if r["entity_type"] == "PROJECT")
 
    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  Papers processed:     {len(papers_with_ack)}")
    print(f"  Total entities:       {len(all_rows)}")
    print(f"    PERSON:             {total_persons}")
    print(f"    ORGANIZATION:       {total_orgs}")
    print(f"    PROJECT (grant ids):{total_projs}")
    print(f"\n  Output → {OUTPUT_CSV}")
    print("Done.")
 
 
if __name__ == "__main__":
    main()