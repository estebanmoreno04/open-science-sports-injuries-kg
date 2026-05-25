from pathlib import Path
import re

import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, XSD, OWL


BASE = Namespace("http://kg.sports-injuries.org/resource/")
ONT = Namespace("http://kg.sports-injuries.org/ontology/")

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
KG_DIR = Path("kg")


def safe_uri(value: str) -> str:
    """Convert arbitrary text into a simple URI-safe fragment."""
    value = str(value).strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9_\-]", "_", value)
    return value


def read_csv_auto(path: Path) -> pd.DataFrame:
    """Read CSV files using either comma or semicolon separator."""
    try:
        return pd.read_csv(path, sep=";")
    except Exception:
        return pd.read_csv(path)


def add_literal_if_present(graph: Graph, subject: URIRef, predicate: URIRef, value, datatype=None):
    """Add a literal triple only if the value is not empty."""
    if pd.isna(value):
        return

    value = str(value).strip()

    if not value:
        return

    if datatype is not None:
        graph.add((subject, predicate, Literal(value, datatype=datatype)))
    else:
        graph.add((subject, predicate, Literal(value)))


def add_papers(graph: Graph):
    papers_path = DATA_DIR / "metadata" / "papers.csv"

    if not papers_path.exists():
        print(f"Skipping papers: file not found at {papers_path}")
        return

    papers = read_csv_auto(papers_path)

    for _, row in papers.iterrows():
        paper_id = row["paper_id"]
        paper_uri = BASE[f"paper/{safe_uri(paper_id)}"]

        graph.add((paper_uri, RDF.type, ONT.Paper))
        graph.add((paper_uri, ONT.paperId, Literal(str(paper_id), datatype=XSD.string)))

        if "title" in row:
            add_literal_if_present(graph, paper_uri, ONT.title, row["title"], XSD.string)

        if "doi" in row:
            add_literal_if_present(graph, paper_uri, ONT.doi, row["doi"], XSD.string)

        if "publication_year" in row and not pd.isna(row["publication_year"]):
            try:
                year = int(row["publication_year"])
                graph.add((paper_uri, ONT.publicationYear, Literal(year, datatype=XSD.integer)))
            except ValueError:
                add_literal_if_present(graph, paper_uri, ONT.publicationYear, row["publication_year"], XSD.string)

        if "abstract" in row:
            add_literal_if_present(graph, paper_uri, ONT.abstractText, row["abstract"], XSD.string)

        if "openAlexId" in row and not pd.isna(row["openAlexId"]):
            openalex_id = str(row["openAlexId"]).strip()
            if openalex_id:
                semopenalex_uri = URIRef(f"https://semopenalex.org/work/{openalex_id}")
                graph.add((paper_uri, OWL.sameAs, semopenalex_uri))


def add_openaire_enrichment(graph: Graph):
    path = PROCESSED_DIR / "openaire_enrichment.csv"

    if not path.exists():
        print("Skipping OpenAIRE enrichment: file not found")
        return

    enrichment = read_csv_auto(path)

    for _, row in enrichment.iterrows():
        paper_uri = BASE[f"paper/{safe_uri(row['paper_id'])}"]

        if "external_keywords" in row:
            keywords = str(row["external_keywords"]).split("|")
            for keyword in keywords:
                keyword = keyword.strip()
                if keyword:
                    graph.add((paper_uri, ONT.externalKeyword, Literal(keyword, datatype=XSD.string)))

        project_name = str(row.get("funding_project", "")).strip()
        grant_id = str(row.get("grant_id", "")).strip()

        if project_name and project_name.lower() != "nan":
            project_uri = BASE[f"project/{safe_uri(project_name)}"]
            graph.add((project_uri, RDF.type, ONT.Project))
            graph.add((project_uri, ONT.projectName, Literal(project_name, datatype=XSD.string)))
            graph.add((paper_uri, ONT.relatedToProject, project_uri))

            if grant_id and grant_id.lower() != "nan":
                graph.add((project_uri, ONT.grantId, Literal(grant_id, datatype=XSD.string)))


def add_similarities(graph: Graph):
    path = PROCESSED_DIR / "similarities.csv"

    if not path.exists():
        print("Skipping similarities: file not found")
        return

    similarities = read_csv_auto(path)

    for _, row in similarities.iterrows():
        source_id = safe_uri(row["paper_id_source"])
        target_id = safe_uri(row["paper_id_target"])

        source_paper = BASE[f"paper/{source_id}"]
        target_paper = BASE[f"paper/{target_id}"]
        sim_uri = BASE[f"similarity/{source_id}_{target_id}"]

        graph.add((sim_uri, RDF.type, ONT.SimilarityLink))
        graph.add((source_paper, ONT.hasSimilarity, sim_uri))
        graph.add((sim_uri, ONT.isSimilarToPaper, target_paper))

        graph.add((sim_uri, ONT.similarityScore, Literal(float(row["similarity_score"]), datatype=XSD.float)))
        graph.add((sim_uri, ONT.similarityThreshold, Literal(float(row["threshold"]), datatype=XSD.float)))
        graph.add((sim_uri, ONT.modelUsed, Literal(str(row["model_used"]), datatype=XSD.string)))


def add_topics(graph: Graph):
    path = PROCESSED_DIR / "topics.csv"

    if not path.exists():
        print("Skipping topics: file not found")
        return

    topics = read_csv_auto(path)

    for _, row in topics.iterrows():
        paper_id = safe_uri(row["paper_id"])
        topic_id = safe_uri(row["topic_id"])

        paper_uri = BASE[f"paper/{paper_id}"]
        topic_uri = BASE[f"topic/{topic_id}"]
        assignment_uri = BASE[f"topic-assignment/{paper_id}_{topic_id}"]

        graph.add((topic_uri, RDF.type, ONT.Topic))
        graph.add((assignment_uri, RDF.type, ONT.TopicAssignment))

        graph.add((paper_uri, ONT.hasTopicAssignment, assignment_uri))
        graph.add((assignment_uri, ONT.assignedToTopic, topic_uri))

        add_literal_if_present(graph, topic_uri, ONT.topicName, row.get("topic_label", ""), XSD.string)
        add_literal_if_present(graph, topic_uri, ONT.topTerms, row.get("top_terms", ""), XSD.string)

        graph.add((assignment_uri, ONT.confidenceScore, Literal(float(row["confidence_score"]), datatype=XSD.float)))
        graph.add((assignment_uri, ONT.topicThreshold, Literal(float(row["threshold"]), datatype=XSD.float)))
        graph.add((assignment_uri, ONT.modelUsed, Literal(str(row["model_used"]), datatype=XSD.string)))


def add_ner_entities(graph: Graph):
    path = PROCESSED_DIR / "ner_entities.csv"

    if not path.exists():
        print("Skipping NER entities: file not found")
        return

    entities = read_csv_auto(path)

    for _, row in entities.iterrows():
        paper_uri = BASE[f"paper/{safe_uri(row['paper_id'])}"]

        entity_type = str(row["entity_type"]).upper().strip()
        normalized_name = str(row["normalized_name"]).strip()
        entity_uri = BASE[f"entity/{entity_type.lower()}/{safe_uri(normalized_name)}"]

        if entity_type == "PERSON":
            graph.add((entity_uri, RDF.type, ONT.Person))
        elif entity_type == "ORGANIZATION":
            graph.add((entity_uri, RDF.type, ONT.Organization))
        elif entity_type == "PROJECT":
            graph.add((entity_uri, RDF.type, ONT.Project))
        else:
            graph.add((entity_uri, RDF.type, ONT.ExtractedEntity))

        graph.add((entity_uri, ONT.name, Literal(normalized_name, datatype=XSD.string)))
        graph.add((paper_uri, ONT.acknowledges, entity_uri))

        if "confidence_score" in row and not pd.isna(row["confidence_score"]):
            graph.add((entity_uri, ONT.confidenceScore, Literal(float(row["confidence_score"]), datatype=XSD.float)))

        if "model_used" in row:
            add_literal_if_present(graph, entity_uri, ONT.modelUsed, row["model_used"], XSD.string)


def build_graph() -> Graph:
    graph = Graph()

    graph.bind("kg", BASE)
    graph.bind("sio", ONT)
    graph.bind("rdf", RDF)
    graph.bind("xsd", XSD)
    graph.bind("owl", OWL)

    add_papers(graph)
    add_openaire_enrichment(graph)
    add_similarities(graph)
    add_topics(graph)
    add_ner_entities(graph)

    return graph


def main():
    KG_DIR.mkdir(exist_ok=True)

    graph = build_graph()

    output_path = KG_DIR / "sports_injuries_kg.ttl"
    graph.serialize(destination=output_path, format="turtle")

    print(f"Knowledge Graph exported to {output_path}")
    print(f"Total triples: {len(graph)}")


if __name__ == "__main__":
    main()