# Sports Injuries Scholarly Knowledge Graph

This repository contains the materials for the **Open Science and AI in Research Software Engineering** group assignment.

The project aims to build a **Scholarly Knowledge Graph** for exploring scientific literature about sports-related lower-limb injuries, including injuries affecting the foot, ankle, knee and lower-limb muscles.

## Current Status

The repository currently contains an integrated version of the project, including:

- A corpus of 30 papers about lower-limb sports injuries.
- Metadata extracted and enriched from SemOpenAlex.
- External keyword enrichment using OpenAIRE.
- Abstract similarity computation using two embedding models from HuggingFace.
- Topic modeling over paper abstracts using BERTopic and LDA.
- Named Entity Recognition over acknowledgements sections using `dslim/bert-base-NER`.
- RDF Knowledge Graph generation in Turtle format.
- A Flask/Cytoscape.js demo for visual exploration.
- Example SPARQL queries for consuming the generated Knowledge Graph.

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
- Which people and organizations are acknowledged in a paper?

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
    acknowledgements.csv
    ner_entities.csv
    similarities.csv
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
  fix_pmc_ids.py
  abstract_similarity.py
  topic_modeling.py
  extract_acknowledgements.py
  ner_acknowledgements.py

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
3. Metadata enrichment using SemOpenAlex SPARQL queries.
   - PMC IDs were verified and corrected using the NCBI ID Converter API
     (`scripts/fix_pmc_ids.py`). 10 out of 23 PMC URLs required correction
     due to differences between the PMC web interface and the OAI API identifiers.
4. External keyword enrichment using OpenAIRE (`scripts/enrich_openAire.py`).
   - Keywords were retrieved for all 30 papers.
   - No funding projects were found, as the corpus is predominantly composed
     of non-European publications not covered by OpenAIRE.
5. Abstract embedding and semantic similarity computation using two models
   (`scripts/abstract_similarity.py`):
   - `sentence-transformers/all-MiniLM-L6-v2`
   - `intfloat/e5-small-v2`
6. Topic modeling over paper abstracts using BERTopic and LDA
   (`scripts/topic_modeling.py`).
7. Acknowledgements extraction from the PMC OAI API
   (`scripts/extract_acknowledgements.py`).
   - Acknowledgements were retrieved for 13 out of 30 papers.
   - Papers without a PMC URL or without an acknowledgements section
     in their XML were not processed.
8. Named Entity Recognition over acknowledgements using `dslim/bert-base-NER`
   from HuggingFace (`scripts/ner_acknowledgements.py`).
   - 67 entities extracted: 10 persons, 56 organizations, 1 grant ID.
   - Grant IDs were detected using regex patterns as a complement to the
     NER model, which does not reliably detect alphanumeric identifiers.
9. RDF Knowledge Graph generation in Turtle format (`src/build_rdf.py`).
10. Visual exploration through a Flask/Cytoscape.js demo (`app.py`).
11. SPARQL query examples for inspecting and reusing the Knowledge Graph
    (`kg/example_queries.sparql`).

## Similarity Modeling

Semantic similarity between paper abstracts was computed using sentence embedding models from HuggingFace. Two candidate models were compared:

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

## NER over Acknowledgements

Named Entity Recognition was applied to the acknowledgements sections extracted from papers available in PubMed Central.

**Extraction**: the PMC OAI API was used to retrieve the full-text XML of each paper with a valid PMC URL. The `<ack>` element and funding-related sections were extracted using regex-based parsing, which is more robust than namespace-aware XML parsing for the heterogeneous JATS XML structure used by PMC.

**Model**: `dslim/bert-base-NER` from HuggingFace, fine-tuned on CoNLL-2003. This model was chosen over biomedical NER models because acknowledgements contain general named entities — people, institutions, funding bodies — rather than clinical terminology.

**Grant ID detection**: a regex-based post-processing step complements the NER model to detect grant and award identifiers (e.g. `W911NF-18-1-0027`, `15PJ1407600`), which NER models do not reliably capture.

**Results**: 67 entities extracted from 13 papers — 10 persons, 56 organizations, 1 grant ID.

**Limitations**: 7 papers had no PMC URL (restricted-access journals such as JOSPT and JBJS Reviews). A further 10 papers had PMC URLs but no acknowledgements section in their XML. These cases are recorded in `data/processed/acknowledgements.csv` with an empty acknowledgements field.

## Knowledge Graph

The main RDF Knowledge Graph is available at:

```text
kg/sports_injuries_kg.ttl
```

The graph represents papers as RDF resources and includes:

- Paper identifiers, titles, publication years, DOIs and abstracts
- SemOpenAlex links using `owl:sameAs`
- Author and affiliation information from SemOpenAlex
- OpenAIRE external keywords
- Topic assignments with confidence scores (BERTopic and LDA)
- Semantic similarity links between papers
- Acknowledged persons, organizations and grant IDs from NER

The RDF generation script is:

```text
src/build_rdf.py
```

## Setup

### Prerequisites

- Python 3.9+
- conda or venv
- Docker (optional, for containerized execution)

### Installation

```bash
git clone https://github.com/estebanmoreno04/open-science-sports-injuries-kg.git
cd open-science-sports-injuries-kg
pip install -r requirements.txt
```

### Credentials

This project uses the OpenAIRE API, which requires a personal access token.
To set up your credentials:

1. Register a free account at https://develop.openaire.eu/
2. Create a new service and select **Basic** security level
3. Copy your `client_id` and `client_secret`
4. Create a `.env` file in the root of the repository:

```bash
cp .env.example .env
```

5. Fill in your credentials in `.env`:

```
OPENAIRE_CLIENT_ID=your_client_id_here
OPENAIRE_CLIENT_SECRET=your_client_secret_here
```

> **Note:** The `.env` file is listed in `.gitignore` and will never be
> committed to the repository. Never share your credentials publicly.

## How to Run

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the full pipeline in order:

```bash
python scripts/enrich_semOpenAlex.py
python scripts/enrich_openAire.py
python scripts/abstract_similarity.py
python scripts/topic_modeling.py
python scripts/extract_acknowledgements.py
python scripts/ner_acknowledgements.py
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

- Explore the 30-paper corpus as an interactive graph
- Visualize semantic similarity links between papers
- Switch between embedding models (MiniLM and E5)
- Adjust the similarity threshold with a slider
- Inspect paper metadata including title, year, DOI and abstract
- View topic assignments from BERTopic and LDA
- Access DOI and SemOpenAlex links directly

## SPARQL Queries

Example SPARQL queries are provided in:

```text
kg/example_queries.sparql
```

These queries cover:

- Listing papers by title and publication year
- Retrieving SemOpenAlex links
- Inspecting OpenAIRE external keywords
- Exploring topic assignments
- Retrieving paper similarity links
- Querying acknowledged entities

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

## AI Usage Declaration

In accordance with Open Science best practices and the requirements of this assignment, we declare the use of Artificial Intelligence tools during the development of this project:

- **Conceptualization and Knowledge Engineering:** Large Language Models (LLMs) were used as an assistant to brainstorm domain-specific keywords, review ontology design decisions, debug code and assist in formatting documentation and Mermaid.js diagrams. All AI-generated suggestions were reviewed, contrasted with the course theory and manually modified by the group members.
- **Data Processing and Machine Learning Support:** AI-assisted tools were used to support the development of scripts for metadata enrichment, semantic similarity computation, topic modeling, NER and RDF generation. The final implementation, model choices, thresholds and outputs were manually reviewed by the group.
- **Natural Language Processing Models:** HuggingFace models and related NLP libraries were used to compute semantic representations of abstracts, compare paper similarity, generate topic modeling outputs and perform named entity recognition over acknowledgements sections.

## Limitations and Future Work

Current limitations include:

- The Knowledge Graph is focused on a relatively small corpus of 30 papers.
- Topic modeling results depend on the size and thematic diversity of the selected corpus.
- Similarity thresholds may need adjustment depending on the desired density of the graph.
- PMC IDs in the initial corpus were partially incorrect due to differences between
  the PMC web interface and the OAI API identifiers. These were corrected
  programmatically using the NCBI ID Converter API (`scripts/fix_pmc_ids.py`).
- NER coverage is limited to 13 papers due to the absence of PMC full-text access
  for restricted-access journals and papers without acknowledgements sections.
- OpenAIRE funding coverage is 0/30 as the corpus is predominantly composed of
  non-European publications not indexed in OpenAIRE with project information.

Future work includes:

- Adding PROV metadata for workflow traceability.
- Packaging the experiment as an RO-Crate.
- Adding Docker support for full environment reproducibility.
- Expanding the corpus to improve topic modeling quality.

## Group Members

- Esteban Moreno Mendoza
- Ignacio Díaz Hernanz
- Mendo Urraca Torrijos
- Juan Manuel Novoa Guevara

## License

This repository is released under the MIT License.

The dataset and metadata are documented separately through `LICENSE-DATA` and `NOTICE`.