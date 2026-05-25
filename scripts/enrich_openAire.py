"""
enrich_openaire.py
==================
Queries the OpenAIRE Graph API for each paper using its DOI and
enriches the Knowledge Graph with:
  - External keywords (externalKeyword data property)
  - Related projects and funding information (Project instances)
 
Credentials are read from a .env file in the repo root:
  OPENAIRE_CLIENT_ID=...
  OPENAIRE_CLIENT_SECRET=...
 
Output:
    data/rdf/openaire_enriched.ttl
 
Usage:
    pip install requests rdflib python-dotenv
    python scripts/enrich_openaire.py
"""
 
import csv
import os
import time
import requests
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, OWL, XSD
from dotenv import load_dotenv
 

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV  = os.path.join(BASE_DIR, "data/metadata/papers.csv")
OUTPUT_TTL = os.path.join(BASE_DIR, "data/rdf/openaire_enriched.ttl")
ENV_FILE   = os.path.join(BASE_DIR, ".env")

TOKEN_URL  = "https://aai.openaire.eu/oidc/token"
API_BASE   = "https://api.openaire.eu"
SLEEP      = 1.0  # seconds between requests
 

KG  = Namespace("http://kg.sports-injuries.org/")
ONT = Namespace("http://kg.sports-injuries.org/ontology/")
 

 
def get_token(client_id: str, client_secret: str) -> str:
    """
    Obtain a Bearer token from OpenAIRE AAI using client credentials.
    Token expires in 1 hour — this function is called fresh each run.
    """
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        timeout=15
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to get OpenAIRE token: HTTP {resp.status_code}\n{resp.text}"
        )
    return resp.json()["access_token"]
 
 
 
def query_openaire(doi: str, token: str) -> dict:
    """
    Query OpenAIRE Graph API for a publication by DOI.
    Returns a dict with 'keywords' (list) and 'projects' (list of dicts).
    """
    result = {"keywords": [], "projects": []}
 
    # Search publication by DOI
    url = f"{API_BASE}/search/publications"
    params = {"doi": doi, "format": "json", "size": 1}
    headers = {"Authorization": f"Bearer {token}"}
 
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"    [WARN] HTTP {resp.status_code} for DOI {doi}")
            return result
 
        data = resp.json()
        results = (
            data.get("response", {})
                .get("results", {})
                .get("result", [])
        )
 
        if not results:
            return result
 
        # Take first result
        metadata = results[0].get("metadata", {}).get("oaf:entity", {})
        pub = metadata.get("oaf:result", {})
 
        subjects = pub.get("subject", [])
        if isinstance(subjects, dict):
            subjects = [subjects]
        for subj in subjects:
            val = subj.get("$", "").strip()
            if val:
                result["keywords"].append(val)
 

        rels = metadata.get("oaf:relation", [])
        if isinstance(rels, dict):
            rels = [rels]
 
        project_ids_seen = set()
        for rel in rels:
            if rel.get("@relationtype") != "resultProject":
                continue
            proj_id = rel.get("to", {}).get("$", "").strip()
            if not proj_id or proj_id in project_ids_seen:
                continue
            project_ids_seen.add(proj_id)
 
            # Query project details
            proj_data = query_project(proj_id, token)
            if proj_data:
                result["projects"].append(proj_data)
 
    except Exception as e:
        print(f"    [ERROR] {e}")
 
    return result
 
 
def query_project(project_id: str, token: str) -> dict:
    """
    Query OpenAIRE for project details by project ID.
    Returns dict with name and grantId, or empty dict on failure.
    """
    url = f"{API_BASE}/search/projects"
    params = {"openaireProjectID": project_id, "format": "json", "size": 1}
    headers = {"Authorization": f"Bearer {token}"}
 
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        results = (
            data.get("response", {})
                .get("results", {})
                .get("result", [])
        )
        if not results:
            return {}
 
        proj = (
            results[0]
            .get("metadata", {})
            .get("oaf:entity", {})
            .get("oaf:project", {})
        )
        name     = proj.get("title", {}).get("$", "").strip()
        grant_id = proj.get("code", {}).get("$", "").strip()
        funder   = (
            proj.get("fundingtree", {})
                .get("funder", {})
                .get("name", {})
                .get("$", "")
                .strip()
        )
        return {
            "id":      project_id,
            "name":    name,
            "grantId": grant_id,
            "funder":  funder,
        }
    except Exception:
        return {}
 
 

 
def build_rdf(g: Graph, paper_id: str, openaire_data: dict) -> None:
    local_uri = KG[f"paper/{paper_id}"]
 
    # External keywords
    for kw in openaire_data.get("keywords", []):
        g.add((local_uri, ONT.externalKeyword,
               Literal(kw, datatype=XSD.string)))
 
    # Projects
    for proj in openaire_data.get("projects", []):
        proj_id  = proj.get("id", "").replace("/", "-").replace(":", "-")
        proj_uri = KG[f"project/{proj_id}"]
 
        g.add((proj_uri, RDF.type, ONT.Project))
 
        if proj.get("name"):
            g.add((proj_uri, ONT.projectName,
                   Literal(proj["name"], datatype=XSD.string)))
        if proj.get("grantId"):
            g.add((proj_uri, ONT.grantId,
                   Literal(proj["grantId"], datatype=XSD.string)))
        if proj.get("funder"):
            g.add((proj_uri, ONT.funderName,
                   Literal(proj["funder"], datatype=XSD.string)))
 
        g.add((local_uri, ONT.relatedToProject, proj_uri))
 
 

 
def main():
    # Load credentials from .env
    load_dotenv(ENV_FILE)
    client_id     = os.getenv("OPENAIRE_CLIENT_ID")
    client_secret = os.getenv("OPENAIRE_CLIENT_SECRET")
 
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing OpenAIRE credentials.\n"
            "Create a .env file in the repo root with:\n"
            "  OPENAIRE_CLIENT_ID=...\n"
            "  OPENAIRE_CLIENT_SECRET=..."
        )
 
    print("Obtaining OpenAIRE access token...")
    token = get_token(client_id, client_secret)
    print("  Token obtained successfully.\n")
 
    # Read CSV
    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        papers = list(reader)
    print(f"  {len(papers)} papers loaded.\n")
 
    os.makedirs(os.path.dirname(OUTPUT_TTL), exist_ok=True)
 
    g = Graph()
    g.bind("kg",  KG)
    g.bind("ont", ONT)
    g.bind("xsd", XSD)
 
    found_kw      = 0
    found_proj    = 0
    not_found     = []
 
    for paper in papers:
        paper_id = (paper.get("paper_id") or "").strip()
        doi      = (paper.get("doi") or "").strip()
 
        if not doi:
            print(f"  [{paper_id}] No DOI — skipping.")
            not_found.append(paper_id)
            continue
 
        print(f"  [{paper_id}] Querying OpenAIRE for DOI {doi}...")
        data = query_openaire(doi, token)
 
        kw_count   = len(data["keywords"])
        proj_count = len(data["projects"])
 
        if kw_count == 0 and proj_count == 0:
            print(f"    → No data found in OpenAIRE.")
            not_found.append(paper_id)
        else:
            print(f"    → {kw_count} keywords | {proj_count} projects")
            if kw_count > 0:
                found_kw += 1
            if proj_count > 0:
                found_proj += 1
 
        build_rdf(g, paper_id, data)
        time.sleep(SLEEP)
 
    print(f"\nSerializing to {OUTPUT_TTL}...")
    g.serialize(destination=OUTPUT_TTL, format="turtle")

    import csv as csv_module
    processed_dir = os.path.join(BASE_DIR, "data/processed")
    os.makedirs(processed_dir, exist_ok=True)
    openaire_csv = os.path.join(processed_dir, "openaire_enrichment.csv")
    openaire_rows = []
    for paper in papers:
        pid = (paper.get("paper_id") or "").strip()
        doi = (paper.get("doi") or "").strip()
        d   = query_openaire(doi, token) if doi else {"keywords": [], "projects": []}
        kws = "|".join(d["keywords"])
        for proj in d["projects"] or [{}]:
            openaire_rows.append({
                "paper_id":         pid,
                "doi":              doi,
                "external_keywords": kws,
                "funding_project":  proj.get("name", ""),
                "grant_id":         proj.get("grantId", ""),
                "source":           "OpenAIRE API",
            })
        if not d["projects"]:
            openaire_rows.append({
                "paper_id":         pid,
                "doi":              doi,
                "external_keywords": kws,
                "funding_project":  "",
                "grant_id":         "",
                "source":           "OpenAIRE API",
            })
    with open(openaire_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=["paper_id","doi","external_keywords","funding_project","grant_id","source"])
        writer.writeheader()
        writer.writerows(openaire_rows)
    print(f"  Intermediate CSV → {openaire_csv}")
 
    print("\n── Summary ──────────────────────────────────────")
    print(f"  Papers queried:          {len(papers)}")
    print(f"  With keywords:           {found_kw}/{len(papers)}")
    print(f"  With projects/funding:   {found_proj}/{len(papers)}")
    print(f"  Total RDF triples:       {len(g)}")
    if not_found:
        print(f"  No data found:           {', '.join(not_found)}")
    print(f"\n  Output → {OUTPUT_TTL}")
    print("Done.")
 
 
if __name__ == "__main__":
    main()