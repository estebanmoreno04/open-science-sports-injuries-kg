# Sports Injuries Scholarly Knowledge Graph

This repository contains the materials for the **Open Science and AI in Research Software Engineering** group assignment.

The project aims to build a **Scholarly Knowledge Graph** for exploring scientific literature about sports-related lower-limb injuries, including injuries affecting the foot, ankle, knee and lower-limb muscles.

## Current Status

The repository currently contains an integrated version of the project, including:

- A corpus of 30 papers about lower-limb sports injuries.
- Metadata extracted and enriched from SemOpenAlex.
- External keyword enrichment using OpenAIRE.
- Abstract similarity computation using embedding models.
- Topic modeling over paper abstracts.
- RDF Knowledge Graph generation in Turtle format.
- A Flask/Cytoscape.js demo for visual exploration.
- Example SPARQL queries for consuming the generated Knowledge Graph.

The Named Entity Recognition step over acknowledgements is planned as part of the final integration.

## Use Case

The proposed application is a literature exploration tool based on a Scholarly Knowledge Graph. It allows users to search and navigate scientific papers about lower-limb sports injuries by connecting papers with injuries, body parts, treatments, authors, organizations, projects, topics and semantic similarity links.

The system is **not intended to provide medical diagnosis or clinical recommendations**. Its purpose is to support the exploration of scientific knowledge in sports medicine.

The application helps answer questions such as:

- Which papers study injuries affecting a specific body part, such as the knee, ankle or foot?
- Which injury types are most frequently associated with each body part?
- Which treatment or rehabilitation methods are described for a given injury?
- Which papers are similar to a selected article?
- Which authors and organizations are most active in a specific injury area?
- Which topics emerge from the selected corpus of scientific papers?
- Which external keywords or projects are associated with each paper?

## Scope

The project focuses on sports medicine papers related to injuries of the lower limb, especially:

- Foot
- Ankle
- Knee
- Lower-limb muscles, such as hamstrings, quadriceps, calf or soleus

The injury types considered include:

- Sprains
- Muscle strains or tears
- Tendinopathies
- Ligament injuries
- Meniscal injuries
- Overuse injuries
- Stress fractures
- Rehabilitation and return-to-play studies

## Selected Sources

The project uses two distinct external sources to satisfy the assignment requirements:

| Source | Type | Purpose |
|---|---|---|
| SemOpenAlex | SPARQL/RDF | Primary source for scholarly entities such as papers, authors, organizations and venues. It provides the core scholarly metadata used in the Knowledge Graph. |
| OpenAIRE | API / Graph | Secondary source used to enrich papers with external keywords and additional project/funding information when available. |

SemOpenAlex provides the scholarly metadata backbone, while OpenAIRE complements the corpus with external thematic keywords and funding/project-related information.

## Repository Structure

```text
docs/
  use_case.md
  sources.md
  ontology.md
  ontology_diagram.mmd
  ontology_diagram.png
  data_schema.md

data/
  raw_papers/
    README.md
  metadata/
    papers.csv
  processed/
    semopenalex_metadata.csv
    openaire_enrichment.csv
    topics.csv
    topics_bertopic.csv
    topics_lda.csv
  rdf/
    semopenalex_enriched.ttl
    openaire_enriched.ttl

kg/
  sports_injuries_kg.ttl
  example_queries.sparql

results/
  similarity/
    similarity_matrix_sentence_transformers_all_MiniLM_L6_v2.csv
    similarity_matrix_intfloat_e5_small_v2.csv
    top3_similar_sentence_transformers_all_MiniLM_L6_v2.csv
    top3_similar_intfloat_e5_small_v2.csv
    run_info_sentence_transformers_all_MiniLM_L6_v2.txt
    run_info_intfloat_e5_small_v2.txt
  topics/
    topics_summary_bertopic.csv
    topics_summary_lda.csv

scripts/
  enrich_semOpenAlex.py
  enrich_openAire.py
  abstract_similarity.py
  topic_modeling.py

src/
  build_rdf.py

templates/
  kg_explorer.html
  kg_explorer_flask.html

app.py
prepare_kg_demo.py
requirements.txt
LICENSE
LICENSE-DATA
NOTICE
```

## Corpus

The current corpus contains 30 papers related to sports injuries of the lower limb.

The main corpus metadata is stored in:

```text
data/metadata/papers.csv
```

Each paper is identified through a stable internal identifier such as `P01`, `P02`, ..., `P30`. This `paper_id` is used consistently across metadata, enrichment files, similarity results, topic modeling outputs and the final RDF Knowledge Graph.

## Current Pipeline

The current version of the project implements the following pipeline:

1. Selection of 30 papers about lower-limb sports injuries.
2. Collection of basic bibliographic metadata.
3. Metadata enrichment using SemOpenAlex.
4. External keyword enrichment using OpenAIRE.
5. Abstract embedding and semantic similarity computation using two models:
   - `sentence-transformers/all-MiniLM-L6-v2`
   - `intfloat/e5-small-v2`
6. Topic modeling over paper abstracts using BERTopic and LDA.
7. RDF Knowledge Graph generation in Turtle format.
8. Visual exploration through a Flask/Cytoscape.js demo.
9. SPARQL query examples for inspecting and reusing the Knowledge Graph.

The NER step over acknowledgements will be integrated in the final version to extract acknowledged people, organizations and projects.

## Similarity Modeling

Semantic similarity between paper abstracts was computed using sentence embedding models from Hugging Face. Two candidate models were compared:

- `sentence-transformers/all-MiniLM-L6-v2`
- `intfloat/e5-small-v2`

Both models were evaluated by computing cosine similarity between the abstract embeddings of the 30 papers. The `intfloat/e5-small-v2` model generally produced higher similarity scores, usually around `0.8-0.9`, while `sentence-transformers/all-MiniLM-L6-v2` produced lower and more conservative scores, usually around `0.6-0.75`.

A manual review was performed over a sample of 10 papers. The evaluation criterion was whether the most similar papers were actually related either by anatomical focus, such as knee, ankle, foot or lower-limb muscles, or by similar recovery, rehabilitation or injury-management approaches.

Although `e5-small-v2` produced higher numerical similarity values, the manual review showed that `all-MiniLM-L6-v2` generated more meaningful and interpretable connections according to these criteria. Therefore, `sentence-transformers/all-MiniLM-L6-v2` was selected as the final model for the demo and the Knowledge Graph similarity links.

Cosine similarity was used as the comparison metric. A threshold of `0.6` was selected for creating similarity links between papers. This threshold was chosen because it provides a connected and explorable graph while still preserving meaningful relations under the selected MiniLM model.

The resulting similarity matrices and top-3 most similar papers are stored in:

```text
results/similarity/
```

## Knowledge Graph

The main RDF Knowledge Graph is available at:

```text
kg/sports_injuries_kg.ttl
```

The graph represents papers as RDF resources and includes information such as:

- Paper identifiers
- Titles
- Publication years
- DOIs
- Abstracts
- SemOpenAlex links using `owl:sameAs`
- OpenAIRE external keywords
- Topic assignments
- Similarity links between papers

The RDF generation script is:

```text
src/build_rdf.py
```

## How to Run

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Generate or update the RDF Knowledge Graph:

```bash
python src/build_rdf.py
```

Run the visual demo:

```bash
python app.py
```

Then open the application in a browser:

```text
http://127.0.0.1:5000
```

The demo allows users to:

- Explore the 30-paper corpus.
- Visualize semantic similarity links between papers.
- Switch between embedding models.
- Adjust the similarity threshold.
- Inspect paper metadata.
- View topic assignments.
- Access DOI and SemOpenAlex links.

## SPARQL Queries

Example SPARQL queries are provided in:

```text
kg/example_queries.sparql
```

These queries can be executed over:

```text
kg/sports_injuries_kg.ttl
```

They cover:

- Listing papers by title and publication year.
- Retrieving SemOpenAlex links.
- Inspecting OpenAIRE external keywords.
- Exploring topic assignments.
- Retrieving paper similarity links.
- Querying project/funding information when available.
- Querying acknowledged entities once NER results are integrated.

Example query:

```sparql
PREFIX sio: <http://kg.sports-injuries.org/ontology/>

SELECT ?paper ?title ?year
WHERE {
  ?paper a sio:Paper ;
         sio:title ?title ;
         sio:publicationYear ?year .
}
ORDER BY ?year ?title
```

## Demo

The repository includes a local interactive demo based on Flask and Cytoscape.js.

The demo loads:

- `kg/sports_injuries_kg.ttl`
- similarity matrices from `results/similarity/`
- topic assignments from `data/processed/topics.csv`

It provides a visual interface for exploring the corpus, inspecting papers and navigating similarity-based connections between articles.

## Data Schema

The expected intermediate files and their columns are documented in:

```text
docs/data_schema.md
```

This file defines the common structure used to integrate metadata, external enrichment, similarity results, topic modeling outputs and NER entities into the final RDF Knowledge Graph.

## AI Usage Declaration

In accordance with Open Science best practices and the requirements of this assignment, we declare the use of Artificial Intelligence tools during the development of this project:

- **Conceptualization and Knowledge Engineering:** Large Language Models (LLMs) were used as an assistant to brainstorm domain-specific keywords, review ontology design decisions, debug code and assist in formatting documentation and Mermaid.js diagrams. All AI-generated suggestions were reviewed, contrasted with the course theory and manually modified by the group members.
- **Data Processing and Machine Learning Support:** AI-assisted tools were used to support the development of scripts for metadata enrichment, semantic similarity computation, topic modeling and RDF generation. The final implementation, model choices, thresholds and outputs were manually reviewed by the group.
- **Natural Language Processing Models:** Hugging Face models and related NLP libraries were used to compute semantic representations of abstracts, compare paper similarity and generate topic modeling outputs.

## Limitations and Future Work

Current limitations include:

- The Knowledge Graph is focused on a relatively small corpus of 30 papers.
- Topic modeling results depend on the size and thematic diversity of the selected corpus.
- Similarity thresholds may need adjustment depending on the desired density of the graph.
- NER over acknowledgements is still pending final integration.
- Some external metadata may be incomplete depending on source availability.

Future work includes:

- Integrating NER results from acknowledgements.
- Adding PROV metadata for workflow traceability.
- Packaging the experiment as an RO-Crate.
- Adding more detailed evaluation of similarity, topic modeling and NER outputs.
- Creating a final release for long-term reproducibility.

## Group Members

- Esteban Moreno Mendoza
- Ignacio Díaz Hernanz
- Mendo Urraca Torrijos
- Juan Manuel Novoa Guevara

## License

This repository is released under the MIT License.

The dataset and metadata are documented separately through `LICENSE-DATA` and `NOTICE`.
