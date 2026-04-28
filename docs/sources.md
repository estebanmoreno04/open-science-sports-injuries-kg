# Selected Sources

This project will use two main external sources to enrich the Scholarly Knowledge Graph: one REST API source and one RDF/SPARQL source.

## Summary

| Source | Type | Purpose |
|---|---|---|
| OpenAlex | REST API | Retrieve metadata about papers, authors, organizations, venues, publication years and DOI information. |
| SemOpenAlex | RDF/SPARQL | Query and link OpenAlex scholarly entities as RDF resources. |

## 1. OpenAlex

**Type:** REST API  
**URL:** https://api.openalex.org/  
**Format:** JSON

OpenAlex will be used as the main source for retrieving metadata about scientific publications related to sports injuries of the lower limb.

From OpenAlex, we expect to enrich the graph with information about:

- papers,
- authors,
- organizations,
- publication venues,
- publication year,
- DOI,
- paper URL,
- concepts or topics.

In the ontology, this source will mainly enrich the following classes:

- `Paper`
- `Person`
- `Organization`
- `Venue`
- `Topic`

Expected properties:

- `title`
- `doi`
- `publicationYear`
- `paperURL`
- `openAlexId`
- `hasAuthor`
- `affiliatedWith`
- `publishedIn`
- `belongsToTopic`

## 2. SemOpenAlex

**Type:** RDF/SPARQL source  
**URL:** https://semopenalex.org/sparql  
**Format:** RDF

SemOpenAlex will be used as the RDF/SPARQL source of the project. It provides OpenAlex data represented as RDF, which allows us to query and link scholarly entities using SPARQL.

From SemOpenAlex, we expect to enrich the graph with:

- RDF URIs for papers,
- RDF URIs for authors,
- RDF URIs for organizations,
- RDF links between papers, authors and institutions,
- external links to OpenAlex entities.

In the ontology, this source will mainly enrich the following classes:

- `Paper`
- `Person`
- `Organization`
- `Venue`
- `Topic`

Expected properties:

- `sameAsExternal`
- `hasAuthor`
- `affiliatedWith`
- `publishedIn`
- `belongsToTopic`
