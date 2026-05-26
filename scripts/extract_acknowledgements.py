"""
extract_acknowledgements.py
===========================
Extracts the Acknowledgements section and funding information from
scientific papers using the PMC OA API (structured XML).

Extracts:
  - <ack> section (acknowledgements text)
  - <funding-group> section (funding sources)
  - <notes notes-type="funding-information"> (funding notes)

Output:
    data/processed/acknowledgements.csv

Columns:
    paper_id | acknowledgements | extraction_method | source

Usage:
    pip install requests
    python scripts/extract_acknowledgements.py
"""

import csv
import os
import re
import time
import requests

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV  = os.path.join(BASE_DIR, "data/metadata/papers.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "data/processed/acknowledgements.csv")

PMC_OAI    = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
SLEEP      = 0.5


# ── Helpers ───────────────────────────────────────────────────────────────────

def pmc_numeric_id(pmc_url: str) -> str:
    """Extract numeric PMC ID from URL. e.g. PMC8161930 → 8161930"""
    match = re.search(r"PMC(\d+)", pmc_url)
    return match.group(1) if match else ""


def extract_text_between_tags(xml: str, tag: str) -> list[str]:
    """
    Extract all text content between opening and closing tags,
    stripping inner XML tags. Works without namespace awareness.
    """
    # Match both <tag ...> and <tag>
    pattern = rf"<{tag}(?:\s[^>]*)?>(.+?)</{tag}>"
    matches = re.findall(pattern, xml, re.DOTALL)
    results = []
    for m in matches:
        # Strip all XML tags to get plain text
        text = re.sub(r"<[^>]+>", " ", m)
        # Decode common XML entities
        text = text.replace("&#8217;", "'").replace("&#8216;", "'")
        text = text.replace("&#8220;", '"').replace("&#8221;", '"')
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&apos;", "'").replace("&quot;", '"')
        # Collapse whitespace
        text = " ".join(text.split())
        if text.strip():
            results.append(text.strip())
    return results


def fetch_acknowledgements(pmc_numeric: str) -> str:
    """
    Fetch full text XML from PMC OAI and extract:
      1. <ack> section (acknowledgements)
      2. <funding-group> institutions
      3. <notes notes-type="funding-information"> text
    Returns combined plain text.
    """
    identifier = f"oai:pubmedcentral.nih.gov:{pmc_numeric}"
    params = {
        "verb": "GetRecord",
        "identifier": identifier,
        "metadataPrefix": "pmc",
    }
    try:
        resp = requests.get(PMC_OAI, params=params, timeout=30)
        if resp.status_code != 200:
            return ""

        xml = resp.text
        parts = []

        # 1. <ack> section — main acknowledgements
        ack_texts = extract_text_between_tags(xml, "ack")
        if ack_texts:
            parts.extend(ack_texts)

        # 2. funding-information notes
        # Find <notes notes-type="funding-information">...</notes>
        funding_pattern = r'<notes[^>]*notes-type=["\']funding-information["\'][^>]*>(.+?)</notes>'
        funding_matches = re.findall(funding_pattern, xml, re.DOTALL)
        for m in funding_matches:
            text = re.sub(r"<[^>]+>", " ", m)
            text = " ".join(text.split())
            if text.strip() and text not in parts:
                parts.append(text.strip())

        # 3. funding-group institutions (as fallback if no ack text)
        if not parts:
            institution_texts = extract_text_between_tags(xml, "institution")
            if institution_texts:
                parts.append("Funding institutions: " + "; ".join(institution_texts))

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

    rows = []
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

        print(f"  [{paper_id}] Fetching PMC{numeric_id}...")
        ack_text = fetch_acknowledgements(numeric_id)

        if ack_text:
            preview = ack_text[:100] + "..." if len(ack_text) > 100 else ack_text
            print(f"    → Found ({len(ack_text)} chars): {preview}")
            found += 1
            method = "PMC OAI API"
        else:
            print(f"    → No acknowledgements found.")
            not_found.append(paper_id)
            method = "PMC OAI API (empty)"

        rows.append({
            "paper_id":          paper_id,
            "acknowledgements":  ack_text,
            "extraction_method": method,
            "source":            pmc_url,
        })
        time.sleep(SLEEP)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["paper_id", "acknowledgements", "extraction_method", "source"]
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