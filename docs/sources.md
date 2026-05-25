# Selected Sources

This project uses two external sources to enrich the Scholarly Knowledge Graph:
one RDF/SPARQL source and one REST API source. These two sources are
complementary and serve different purposes.

## Summary

| Source | Type | Purpose |
|---|---|---|
| SemOpenAlex | RDF/SPARQL | Primary source for paper metadata, authors, affiliations and venues as RDF resources. |
| OpenAIRE | REST API | Source for project and funding information, and externally assigned keywords. |

## 1. SemOpenAlex

**Type:** RDF/SPARQL  
**URL:** https://semopenalex.org/sparql  
**Format:** RDF (Turtle, JSON-LD)

SemOpenAlex is OpenAlex data represented as RDF. It is the primary source
for retrieving metadata about scientific publications and linking local
entities to the global Linked Data cloud via `owl:sameAs`.

From SemOpenAlex, we will enrich the graph with:

- paper metadata (title, abstract, DOI, publication year, URL)
- authors and their affiliations to organizations
- publication venues (journal or conference name and type)
- RDF URIs for papers, authors and organizations, used to generate
  `owl:sameAs` links between local entities and SemOpenAlex resources

In the ontology, this source enriches the following classes:

- `Paper`
- `Person`
- `Organization`
- `Venue`

Expected properties from this source:

| Property | Type | Description |
|---|---|---|
| `title` | data | Title of the paper. |
| `abstractText` | data | Abstract of the paper. |
| `doi` | data | Digital Object Identifier. |
| `publicationYear` | data | Year of publication. |
| `paperURL` | data | URL of the paper. |
| `openAlexId` | data | OpenAlex identifier, used to construct `owl:sameAs` links. |
| `hasAuthor` | object | Links a paper to its authors. |
| `affiliatedWith` | object | Links an author to an institution. |
| `publishedIn` | object | Links a paper to its venue. |

> **Note on `owl:sameAs`**: local entities of type `Paper`, `Person` and
> `Organization` will be linked to their SemOpenAlex equivalents using the
> standard W3C property `owl:sameAs`. This property is not defined in our
> ontology; it is reused directly. Example:
> `<http://kg.sports-injuries.org/paper/W123> owl:sameAs <https://semopenalex.org/work/W123>`

## 2. OpenAIRE

**Type:** REST API  
**URL:** https://graph.openaire.eu/docs/apis/home/  
**Format:** JSON

OpenAIRE will be used to retrieve project and funding information associated
with papers, and to obtain externally assigned keywords. These keywords are
stored in the `externalKeyword` data property of `Paper` and are distinct
from the `Topic` clusters generated locally by the ML pipeline.

From OpenAIRE, we will enrich the graph with:

- research projects and grants linked to papers
- grant identifiers
- externally assigned keywords for papers

In the ontology, this source enriches the following classes:

- `Paper`
- `Project`

Expected properties from this source:

| Property | Type | Description |
|---|---|---|
| `externalKeyword` | data | Keywords assigned to the paper by OpenAIRE. Not to be confused with locally generated `Topic` clusters. |
| `relatedToProject` | object | Links a paper to a research project or grant. |
| `projectName` | data | Name of the project. |
| `grantId` | data | Grant identifier as provided by OpenAIRE. |

## 3. PubMed Central (PMC) and Grobid

**Type:** REST API (PMC) + Local tool (Grobid)  
**PMC API URL:** https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/  
**Grobid:** https://github.com/kermitt2/grobid  

These two tools are used together to extract the full text of papers,
specifically the Acknowledgements section, which is required as input
for the NER pipeline.

### Strategy

- **Papers with `pmc_url`** (17 out of 30): full text is retrieved
  directly from the PMC Open Access API in structured XML format.
  The acknowledgements section is extracted as a clean text field
  without requiring PDF parsing.

- **Papers without `pmc_url`** (remaining papers): PDFs are downloaded
  from the publisher URL and processed locally with Grobid, which
  parses the PDF structure and extracts named sections including
  acknowledgements.

### Coverage limitation

Several papers in the corpus are published in restricted-access journals
(e.g. JOSPT, JBJS Reviews) and do not have a PMC URL. For these, Grobid
is used as a fallback. If neither source provides accessible full text,
the paper will have no `acknowledges` triples in the Knowledge Graph.
This limitation is recorded in the PROV trace of the NER experiment.

### What this source enriches

This source does not add new classes to the ontology. It provides the
raw text that the NER model processes to populate the following
properties:

| Property | Description |
|---|---|
| `acknowledges` | Links a paper to acknowledged persons or organizations extracted from the acknowledgements section. |
| `relatedToProject` | Complements OpenAIRE data with project mentions found in the acknowledgements text. |

## Important distinctions

**OpenAlex vs SemOpenAlex**: these are not two separate sources.
SemOpenAlex is OpenAlex data serialised as RDF. Using both would mean
querying the same data twice in different formats. This project uses only
SemOpenAlex as the single access point for OpenAlex data.

**External keywords vs Topic modeling**: the `externalKeyword` property
stores keywords provided by OpenAIRE. These are human-assigned labels and
are not the result of any ML algorithm. The `Topic` class and all
`TopicAssignment` instances are generated locally by applying BERTopic or
LDA on the paper abstracts. These two things must not be confused.