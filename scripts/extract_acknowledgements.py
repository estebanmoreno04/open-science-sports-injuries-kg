"""
extract_acknowledgements.py
===========================
Extracts the Acknowledgements section from scientific papers using
the NCBI Entrez API (efetch endpoint).

This approach does not require PDFs or authentication.
It uses the PMC numeric ID from the papers.csv pmc_url column.

Why Entrez instead of PMC OAI:
  The PMC OAI API applies aggressive rate limiting that blocks automated
  requests. The Entrez efetch API is more tolerant and is the recommended
  programmatic access method for PMC full-text content.

Input:  data/metadata/papers.csv
Output: data/processed/acknowledgements.csv

Columns:
    paper_id | acknowledgements | extraction_method | source

Usage:
    python scripts/extract_acknowledgements.py
"""

import csv
import os
import re
import time
import requests
from xml.etree import ElementTree as ET

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV  = os.path.join(BASE_DIR, "data/metadata/papers.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "data/processed/acknowledgements.csv")

ENTREZ_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SLEEP      = 0.4   # NCBI recommends max 3 requests/second without API key

PARAMS_BASE = {
    "db":      "pmc",
    "rettype": "xml",
    "tool":    "sports-injuries-kg",
    "email":   "juanmanuel.novoa.guevara@alumnos.upm.es",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def pmc_numeric_id(pmc_url: str) -> str:
    """Extract numeric PMC ID from URL. e.g. .../PMC8161930/ → 8161930"""
    match = re.search(r"PMC(\d+)", pmc_url)
    return match.group(1) if match else ""


def extract_text_from_element(elem) -> str:
    """Recursively extract all text from an XML element."""
    texts = []
    if elem.text and elem.text.strip():
        texts.append(elem.text.strip())
    for child in elem:
        texts.append(extract_text_from_element(child))
        if child.tail and child.tail.strip():
            texts.append(child.tail.strip())
    return " ".join(t for t in texts if t)


def fetch_acknowledgements(pmc_numeric: str) -> str:
    """
    Fetch full-text XML from NCBI Entrez and extract acknowledgements.

    Entrez returns JATS XML. Acknowledgements appear in:
      - <ack> element
      - <notes notes-type="funding-information">
      - <funding-group> with <institution> elements
    """
    params = {**PARAMS_BASE, "id": pmc_numeric}

    try:
        resp = requests.get(ENTREZ_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"    [WARN] HTTP {resp.status_code}")
            return ""

        xml = resp.text
        parts = []

        # Strategy 1: regex on <ack> element (most reliable across JATS versions)
        ack_matches = re.findall(
            r"<ack(?:\s[^>]*)?>(.+?)</ack>",
            xml, re.DOTALL
        )
        for m in ack_matches:
            text = re.sub(r"<[^>]+>", " ", m)
            text = text.replace("&#8217;", "'").replace("&#8216;", "'")
            text = text.replace("&#8220;", '"').replace("&#8221;", '"')
            text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            text = " ".join(text.split())
            if text.strip():
                parts.append(text.strip())

        # Strategy 2: funding-information notes
        funding_matches = re.findall(
            r'<notes[^>]*notes-type=["\']funding-information["\'][^>]*>(.+?)</notes>',
            xml, re.DOTALL
        )
        for m in funding_matches:
            text = re.sub(r"<[^>]+>", " ", m)
            text = " ".join(text.split())
            if text.strip() and text not in parts:
                parts.append(text.strip())

        # Strategy 3: funding-group institutions (fallback)
        if not parts:
            inst_matches = re.findall(r"<institution>(.+?)</institution>", xml)
            if inst_matches:
                parts.append("Funding institutions: " + "; ".join(inst_matches))

        return " | ".join(parts) if parts else ""

    except Exception as e:
        print(f"    [ERROR] {e}")
        return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        papers = list(reader)
    print(f"  {len(papers)} papers loaded.\n")

    rows      = []
    found     = 0
    not_found = []

    for paper in papers:
        paper_id = (paper.get("paper_id") or "").strip()
        pmc_url  = (paper.get("pmc_url") or "").strip()

        if not pmc_url:
            print(f"  [{paper_id}] No PMC URL — skipping.")
            rows.append({
                "paper_id":          paper_id,
                "acknowledgements":  "",
                "extraction_method": "none",
                "source":            "",
            })
            not_found.append(paper_id)
            continue

        numeric_id = pmc_numeric_id(pmc_url)
        if not numeric_id:
            print(f"  [{paper_id}] Could not parse PMC ID from {pmc_url}")
            rows.append({
                "paper_id":          paper_id,
                "acknowledgements":  "",
                "extraction_method": "none",
                "source":            pmc_url,
            })
            not_found.append(paper_id)
            continue

        print(f"  [{paper_id}] Fetching PMC{numeric_id} via Entrez...")
        ack_text = fetch_acknowledgements(numeric_id)

        if ack_text:
            preview = ack_text[:100] + "..." if len(ack_text) > 100 else ack_text
            print(f"    → Found ({len(ack_text)} chars): {preview}")
            found += 1
            method = "NCBI Entrez API"
        else:
            print(f"    → No acknowledgements found.")
            not_found.append(paper_id)
            method = "NCBI Entrez API (empty)"

        rows.append({
            "paper_id":          paper_id,
            "acknowledgements":  ack_text,
            "extraction_method": method,
            "source":            pmc_url,
        })
        time.sleep(SLEEP)

    # Safety: do not overwrite existing data if run returned nothing
    if found == 0 and os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
        if any(r.get("acknowledgements") for r in existing):
            print("\n[WARN] No acknowledgements found but existing CSV has data.")
            print("       Keeping existing CSV to avoid data loss.")
            return

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["paper_id", "acknowledgements", "extraction_method", "source"],
            delimiter=";"
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  Papers processed:         {len(papers)}")
    print(f"  With acknowledgements:    {found}/{len(papers)}")
    print(f"  Without acknowledgements: {len(not_found)}")
    if not_found:
        print(f"  Missing: {', '.join(not_found)}")
    print(f"\n  Output → {OUTPUT_CSV}")
    print("Done.")


if __name__ == "__main__":
    main()