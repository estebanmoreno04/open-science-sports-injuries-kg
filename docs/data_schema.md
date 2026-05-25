# Data Schema

This document defines the common intermediate files used to integrate all parts of the pipeline into the final Knowledge Graph.

All intermediate files must use `paper_id` as the common identifier. This makes it possible to merge metadata, enrichment, similarity, topic modeling and NER results into the final RDF Knowledge Graph.

## `data/metadata/papers.csv`

Main corpus file.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier, e.g. P01 |
| title | Paper title |
| authors | Original author string |
| publication_year | Publication year |
| doi | DOI |
| doi_url | DOI URL |
| publisher_url | Publisher page |
| pmc_url | PubMed Central URL, if available |
| pubmed_url | PubMed URL, if available |
| openAlexId | OpenAlex work identifier |
| abstract | Paper abstract |

## `data/processed/semopenalex_metadata.csv`

Metadata retrieved or completed from SemOpenAlex.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| openalex_work_uri | SemOpenAlex/OpenAlex work URI |
| title | Paper title |
| doi | DOI |
| publication_year | Publication year |
| venue_name | Journal or conference name |
| authors | Normalized list of authors |
| affiliations | Author affiliations |
| source | External source used |

## `data/processed/openaire_enrichment.csv`

External enrichment from OpenAIRE.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| doi | DOI used for lookup |
| external_keywords | Keywords retrieved from OpenAIRE |
| funding_project | Related project or funding programme |
| grant_id | Grant identifier |
| source | External source used |

## `data/processed/abstracts.csv`

Clean abstracts used for topic modeling and similarity.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| abstract | Clean abstract text |
| source | Source of the abstract |

## `data/processed/acknowledgements.csv`

Acknowledgements text used for NER.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| acknowledgements | Extracted acknowledgements section |
| extraction_method | PMC, Grobid or manual fallback |
| source | Source file or URL |

## `data/processed/similarities.csv`

Similarity links between papers.

| Column | Description |
|---|---|
| paper_id_source | Source paper |
| paper_id_target | Target paper |
| similarity_score | Cosine similarity score |
| threshold | Similarity threshold used |
| model_used | Embedding model used |

## `data/processed/topics.csv`

Topic modeling results.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| topic_id | Local topic identifier |
| topic_label | Human-readable topic label |
| top_terms | Representative terms of the topic |
| confidence_score | Topic assignment confidence |
| threshold | Topic assignment threshold |
| model_used | Topic modeling model used |

## `data/processed/ner_entities.csv`

Entities extracted from acknowledgements.

| Column | Description |
|---|---|
| paper_id | Internal paper identifier |
| entity_text | Original extracted entity |
| entity_type | PERSON, ORGANIZATION or PROJECT |
| normalized_name | Normalized entity name |
| confidence_score | NER confidence score |
| model_used | NER model used |
| source_section | Usually acknowledgements |

## `kg/sports_injuries_kg.ttl`

Final RDF/Turtle Knowledge Graph.

This file is generated from:

- `data/metadata/papers.csv`
- `data/processed/semopenalex_metadata.csv`
- `data/processed/openaire_enrichment.csv`
- `data/processed/similarities.csv`
- `data/processed/topics.csv`
- `data/processed/ner_entities.csv`

## Integration rule

Every script must preserve the original `paper_id` values from `data/metadata/papers.csv`.

No script should create a new independent identifier for papers.