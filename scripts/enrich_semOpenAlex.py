"""
enrich_semopenalex.py
=====================
Queries the SemOpenAlex SPARQL endpoint for each paper using its
OpenAlex Work URI (e.g. https://semopenalex.org/work/W4205961923)
and generates RDF triples in Turtle format following the project ontology.
 
Strategy (from session 9 slides):
  - Use the openAlexId (W...) from papers.csv to build the SemOpenAlex URI
  - Query all properties of that work directly by URI
  - Generate local RDF triples + owl:sameAs links to SemOpenAlex
 
Output:
    data/rdf/semopenalex_enriched.ttl
 
Usage:
    pip install requests rdflib
    python scripts/enrich_semopenalex.py
"""
 
import csv
import time
import os
import requests
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, OWL, XSD
 
# ── Paths (relative to repo root) ────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV  = os.path.join(BASE_DIR, "data/metadata/papers.csv")
OUTPUT_TTL = os.path.join(BASE_DIR, "data/rdf/semopenalex_enriched.ttl")
 
SPARQL_ENDPOINT = "https://semopenalex.org/sparql"
SLEEP = 1.0  # seconds between queries
 
# ── Namespaces ────────────────────────────────────────────────────────────────
KG  = Namespace("http://kg.sports-injuries.org/")
ONT = Namespace("http://kg.sports-injuries.org/ontology/")
SOA = Namespace("https://semopenalex.org/ontology/")
 
# ── SPARQL query ──────────────────────────────────────────────────────────────
QUERY_TEMPLATE = """
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX soa:     <https://semopenalex.org/ontology/>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
 
SELECT DISTINCT
    ?title
    ?year
    ?venueName
    ?authorUri
    ?authorName
    ?orcid
    ?orgUri
    ?orgName
    ?orgCountry
WHERE {{
    OPTIONAL {{ <{work_uri}> dcterms:title ?title }}
    OPTIONAL {{ <{work_uri}> dcterms:created ?year }}
    OPTIONAL {{
        <{work_uri}> soa:hasHostVenue ?venue .
        ?venue rdfs:label ?venueName
    }}
    OPTIONAL {{
        <{work_uri}> soa:hasAuthorship ?authorship .
        ?authorship soa:hasAuthor ?authorUri .
        OPTIONAL {{ ?authorUri foaf:name ?authorName }}
        OPTIONAL {{ ?authorUri soa:orcid ?orcid }}
        OPTIONAL {{
            ?authorship soa:hasOrganization ?orgUri .
            OPTIONAL {{ ?orgUri foaf:name ?orgName }}
            OPTIONAL {{ ?orgUri soa:countryCode ?orgCountry }}
        }}
    }}
}}
LIMIT 100
"""
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def sparql_query(work_uri: str) -> list:
    query = QUERY_TEMPLATE.format(work_uri=work_uri)
    try:
        resp = requests.post(
            SPARQL_ENDPOINT,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"    [WARN] HTTP {resp.status_code}")
            return []
        data = resp.json()
        bindings = data.get("results", {}).get("bindings", [])
        return [{k: v.get("value", "") for k, v in b.items()} for b in bindings]
    except Exception as e:
        print(f"    [ERROR] {e}")
        return []
 
 
def safe_uri(base: str, value: str) -> URIRef:
    clean = value.strip().replace(" ", "_").replace("/", "-")
    return URIRef(base + clean)
 
 
def build_rdf(g: Graph, paper_id: str, doi: str, abstract: str,
              openalex_id: str, rows: list) -> None:
 
    local_uri    = KG[f"paper/{paper_id}"]
    soa_work_uri = URIRef(f"https://semopenalex.org/work/{openalex_id}")
 
    g.add((local_uri, RDF.type, ONT.Paper))
    g.add((local_uri, ONT.doi, Literal(doi, datatype=XSD.string)))
    g.add((local_uri, ONT.openAlexId, Literal(openalex_id, datatype=XSD.string)))
    g.add((local_uri, OWL.sameAs, soa_work_uri))
 
    if abstract:
        g.add((local_uri, ONT.abstractText, Literal(abstract, datatype=XSD.string)))
 
    if not rows:
        return
 
    first = rows[0]
 
    if first.get("title"):
        g.add((local_uri, ONT.title,
               Literal(first["title"], datatype=XSD.string)))
 
    if first.get("year"):
        try:
            year_val = int(str(first["year"])[:4])
            g.add((local_uri, ONT.publicationYear,
                   Literal(year_val, datatype=XSD.integer)))
        except ValueError:
            pass
 
    venues_seen = set()
    for row in rows:
        vname = row.get("venueName", "").strip()
        if vname and vname not in venues_seen:
            venues_seen.add(vname)
            venue_uri = safe_uri(str(KG) + "venue/", vname)
            g.add((venue_uri, RDF.type, ONT.Venue))
            g.add((venue_uri, ONT.venueName, Literal(vname, datatype=XSD.string)))
            g.add((local_uri, ONT.publishedIn, venue_uri))
 
    authors_seen = set()
    for row in rows:
        author_uri_str = row.get("authorUri", "").strip()
        if not author_uri_str or author_uri_str in authors_seen:
            continue
        authors_seen.add(author_uri_str)
 
        author_uri = URIRef(author_uri_str)
        g.add((author_uri, RDF.type, ONT.Person))
        g.add((author_uri, OWL.sameAs, author_uri))
 
        author_name = row.get("authorName", "").strip()
        if author_name:
            g.add((author_uri, ONT.name, Literal(author_name, datatype=XSD.string)))
 
        orcid = row.get("orcid", "").strip()
        if orcid:
            g.add((author_uri, ONT.orcid, Literal(orcid, datatype=XSD.string)))
 
        g.add((local_uri, ONT.hasAuthor, author_uri))
        g.add((author_uri, ONT.authorOf, local_uri))
 
        org_uri_str = row.get("orgUri", "").strip()
        if org_uri_str:
            org_uri = URIRef(org_uri_str)
            g.add((org_uri, RDF.type, ONT.Organization))
            g.add((org_uri, OWL.sameAs, org_uri))
 
            org_name = row.get("orgName", "").strip()
            if org_name:
                g.add((org_uri, ONT.name, Literal(org_name, datatype=XSD.string)))
 
            org_country = row.get("orgCountry", "").strip()
            if org_country:
                g.add((org_uri, ONT.countryCode,
                       Literal(org_country, datatype=XSD.string)))
 
            g.add((author_uri, ONT.affiliatedWith, org_uri))
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main():
    os.makedirs(os.path.dirname(OUTPUT_TTL), exist_ok=True)
 
    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        papers = list(reader)
    print(f"  {len(papers)} papers loaded.\n")
 
    g = Graph()
    g.bind("kg",  KG)
    g.bind("ont", ONT)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)
    g.bind("soa", SOA)
 
    found      = 0
    not_found  = []
 
    for paper in papers:
        paper_id    = (paper.get("paper_id") or "").strip()
        doi         = (paper.get("doi") or "").strip()
        abstract    = (paper.get("abstract") or "").strip()
        openalex_id = (paper.get("openAlexId") or "").strip()
 
        if not openalex_id:
            print(f"  [{paper_id}] No openAlexId — skipping.")
            not_found.append(paper_id)
            continue
 
        work_uri = f"https://semopenalex.org/work/{openalex_id}"
        print(f"  [{paper_id}] Querying {work_uri}...")
 
        rows = sparql_query(work_uri)
 
        has_data = any(
            row.get("title") or row.get("authorName") or row.get("venueName")
            for row in rows
        ) if rows else False
 
        if has_data:
            authors = len({r.get("authorUri") for r in rows if r.get("authorUri")})
            venue   = rows[0].get("venueName", "—")
            print(f"    → {authors} authors | venue: {venue}")
            found += 1
        else:
            print(f"    → Not found or empty in SemOpenAlex.")
            not_found.append(paper_id)
            rows = []
 
        build_rdf(g, paper_id, doi, abstract, openalex_id, rows)
        time.sleep(SLEEP)
 
    print(f"\nSerializing to {OUTPUT_TTL}...")
    g.serialize(destination=OUTPUT_TTL, format="turtle")
 
    print("\n── Summary ──────────────────────────────────────")
    print(f"  Papers queried:       {len(papers)}")
    print(f"  Found in SemOpenAlex: {found}/{len(papers)}")
    print(f"  Total RDF triples:    {len(g)}")
    if not_found:
        print(f"  Not enriched:         {', '.join(not_found)}")
    print(f"\n  Output → {OUTPUT_TTL}")
    print("Done.")
 
 
if __name__ == "__main__":
    main()
 