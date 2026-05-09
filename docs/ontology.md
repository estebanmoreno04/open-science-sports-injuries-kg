# Ontology Description

This document describes the first version of the ontology for the Scholarly Knowledge Graph. The model includes the base scholarly entities required for the assignment and a small set of domain-specific classes for the use case on sports-related lower-limb injuries.

## Main Classes

### Base Classes

| Class | Description |
|---|---|
| `Paper` | Scientific article included in the corpus. |
| `Person` | Author of a paper or person mentioned in acknowledgements. |
| `Organization` | University, hospital, research center, laboratory, company or funding body. |
| `Project` | Research project or grant associated with a paper. |
| `Topic` | Cluster generated locally by a Machine Learning topic modeling algorithm (e.g., BERTopic or LDA) applied over the paper abstracts. This is not an external keyword or concept from any API. |
| `TopicAssignment` | N-ary class representing the assignment of a paper to a locally generated topic. It stores the confidence score and the threshold applied by the model. |
| `SimilarityLink` | N-ary class representing a similarity relationship between two papers. It stores the cosine similarity score and the threshold used to decide whether the link is created. |

### Domain Classes

| Class | Description |
|---|---|
| `BodyPart` | Anatomical part of the lower limb, such as knee, ankle, foot, hamstring or quadriceps. |
| `Injury` | Type of sports injury, such as ankle sprain, ACL tear, meniscus injury, hamstring strain or tendinopathy. |
| `TreatmentMethod` | Treatment, rehabilitation method or intervention described in a paper. |
| `Venue` | Journal, conference or publication venue where a paper was published. |
| `Sport` | Sport or physical activity context, such as football, basketball, running or athletics. |
| `ClinicalMeasure` | Clinical or recovery-related measure reported in a paper, such as pain score, recovery time or return-to-play time. |

## Object Properties

| Property | Domain | Range | Origin / Justification | Description |
|---|---|---|---|---|
| `hasTopicAssignment` | `Paper` | `TopicAssignment` | **Local ML (Session 10)** | Links a paper to its n-ary topic assignment node. |
| `assignedToTopic` | `TopicAssignment` | `Topic` | **Local ML (Session 10)** | Links the assignment node to the locally generated topic cluster. |
| `hasSimilarity` | `Paper` | `SimilarityLink` | **Local ML (Session 10)** | Links a paper to its n-ary similarity node. |
| `isSimilarToPaper` | `SimilarityLink` | `Paper` | **Local ML (Session 10)** | Links the similarity node to the target similar paper. |
| `acknowledges` | `Paper` | `Person` / `Organization` | **NER (Session 11)** | Links a paper to acknowledged people or organizations extracted from the acknowledgements section. |
| `hasAuthor` | `Paper` | `Person` | **SemOpenAlex SPARQL** | Links a paper to one of its authors. |
| `authorOf` | `Person` | `Paper` | **SemOpenAlex SPARQL** | Inverse relation of `hasAuthor`. |
| `affiliatedWith` | `Person` | `Organization` | **SemOpenAlex SPARQL** | Links an author to an institution or organization. |
| `relatedToProject` | `Paper` | `Project` | **OpenAIRE API** | Links a paper to a research project or grant. |
| `studiesInjury` | `Paper` | `Injury` | **NER (Session 11)** | Indicates that a paper studies a specific injury. |
| `affectsBodyPart` | `Injury` | `BodyPart` | **NER (Session 11)** | Indicates the body part affected by an injury. |
| `focusesOnBodyPart` | `Paper` | `BodyPart` | **NER (Session 11)** | Direct shortcut relation between a paper and the body part studied. Can be inferred via `Paper → studiesInjury → Injury → affectsBodyPart → BodyPart`. |
| `describesTreatment` | `Paper` | `TreatmentMethod` | **NER (Session 11)** | Indicates that a paper describes or evaluates a treatment method. |
| `appliedToInjury` | `TreatmentMethod` | `Injury` | **NER (Session 11)** | Links a treatment method to the injury it addresses. |
| `evaluatedInSport` | `Paper` | `Sport` | **NER (Session 11)** | Links a paper to the sport context studied. |
| `publishedIn` | `Paper` | `Venue` | **SemOpenAlex SPARQL** | Links a paper to its journal or conference. |
| `reportsMeasure` | `Paper` | `ClinicalMeasure` | **NER (Session 11)** | Links a paper to a clinical or recovery-related measure. |

## Data Properties

### Paper

| Property | Type | Origin | Description |
|---|---|---|---|
| `title` | `xsd:string` | SemOpenAlex | Title of the paper. |
| `abstractText` | `xsd:string` | SemOpenAlex | Abstract of the paper. Used as input for topic modeling and similarity computation. |
| `doi` | `xsd:string` | SemOpenAlex | Digital Object Identifier. |
| `publicationYear` | `xsd:integer` | SemOpenAlex | Year of publication. |
| `paperURL` | `xsd:anyURI` | SemOpenAlex | URL of the paper. |
| `openAlexId` | `xsd:string` | SemOpenAlex | OpenAlex identifier, used to construct the `owl:sameAs` link to SemOpenAlex. |
| `externalKeyword` | `xsd:string` | OpenAIRE API | Keywords assigned externally by OpenAIRE. Distinct from the locally generated `Topic` clusters. |

### TopicAssignment

| Property | Type | Description |
|---|---|---|
| `confidenceScore` | `xsd:float` | Probability score assigned by the topic model to this paper-topic pair. Value between 0.0 and 1.0. |
| `topicThreshold` | `xsd:float` | Minimum confidence score required to create this assignment. See Threshold Criteria section. |
| `assignmentDate` | `xsd:date` | Date when the topic model was applied. |
| `modelUsed` | `xsd:string` | Name of the topic modeling algorithm used (e.g., BERTopic, LDA). |

### SimilarityLink

| Property | Type | Description |
|---|---|---|
| `similarityScore` | `xsd:float` | Cosine similarity score between the abstract embeddings of the two papers. Value between 0.0 and 1.0. |
| `similarityThreshold` | `xsd:float` | Minimum cosine similarity score required to create this link. See Threshold Criteria section. |
| `calculationDate` | `xsd:date` | Date when the similarity score was calculated. |
| `modelUsed` | `xsd:string` | Name of the embedding model used (e.g., all-MiniLM-L6-v2). |

### Person

| Property | Type | Description |
|---|---|---|
| `name` | `xsd:string` | Full name of the person. |
| `orcid` | `xsd:string` | ORCID identifier, if available. |
| `givenName` | `xsd:string` | Given name. |
| `familyName` | `xsd:string` | Family name. |

### Organization

| Property | Type | Description |
|---|---|---|
| `name` | `xsd:string` | Name of the organization. |
| `countryName` | `xsd:string` | Country where the organization is located. |
| `countryCode` | `xsd:string` | ISO country code. |
| `organizationType` | `xsd:string` | Type: education, healthcare, company or research institute. |
| `openAlexId` | `xsd:string` | OpenAlex identifier, used to construct the `owl:sameAs` link. |

### Project

| Property | Type | Description |
|---|---|---|
| `projectName` | `xsd:string` | Name of the project or grant. |
| `grantId` | `xsd:string` | Grant identifier as provided by OpenAIRE. |

### Topic

| Property | Type | Description |
|---|---|---|
| `topicName` | `xsd:string` | Human-readable label assigned to the cluster after manual inspection of its top terms. |
| `topicDescription` | `xsd:string` | Short description of the topic. |
| `topTerms` | `xsd:string` | Most representative terms of the topic as output by the ML model. |

### BodyPart

| Property | Type | Description |
|---|---|---|
| `bodyPartName` | `xsd:string` | Name of the body part. |
| `bodyRegion` | `xsd:string` | Anatomical region, for example lower limb. |
| `synonymLabel` | `xsd:string` | Alternative labels or synonyms. |

### Injury

| Property | Type | Description |
|---|---|---|
| `injuryName` | `xsd:string` | Name of the injury. |
| `injuryCategory` | `xsd:string` | Category: ligament, muscle, tendon, bone or overuse. |
| `injuryDescription` | `xsd:string` | Short textual description of the injury. |

### TreatmentMethod

| Property | Type | Description |
|---|---|---|
| `treatmentName` | `xsd:string` | Name of the treatment or rehabilitation method. |
| `treatmentType` | `xsd:string` | Type: surgery, physiotherapy, exercise, prevention or recovery protocol. |
| `treatmentDescription` | `xsd:string` | Short description of the treatment. |

### Venue

| Property | Type | Description |
|---|---|---|
| `venueName` | `xsd:string` | Name of the journal or conference. |
| `venueType` | `xsd:string` | Type of venue: journal or conference. |

### Sport

| Property | Type | Description |
|---|---|---|
| `sportName` | `xsd:string` | Name of the sport or activity. |

### ClinicalMeasure

| Property | Type | Description |
|---|---|---|
| `measureName` | `xsd:string` | Name of the clinical or recovery-related measure. |
| `measureUnit` | `xsd:string` | Unit of measurement, if applicable. |

## Threshold Criteria

The n-ary classes `TopicAssignment` and `SimilarityLink` store threshold values that control when a relationship is created. These thresholds are recorded as data properties so that any consumer of the KG can understand and reproduce the decisions made by the ML pipeline.

### Topic Assignment Threshold

A `TopicAssignment` instance is created between a `Paper` and a `Topic` only if the confidence score returned by the topic model is **equal to or greater than 0.4**.

- **Rationale**: a value of 0.4 avoids assigning papers to topics where the model has low confidence. Papers may have more than one `TopicAssignment` if multiple topics exceed this threshold (soft clustering).
- The threshold is stored in the `topicThreshold` property of each instance, allowing it to be adjusted in future runs without changing the ontology.

### Similarity Threshold

A `SimilarityLink` instance is created between two `Paper` entities only if the cosine similarity between their abstract embeddings is **equal to or greater than 0.75**.

- **Rationale**: cosine similarity above 0.75 indicates strong semantic overlap between abstracts when using sentence transformer models such as `all-MiniLM-L6-v2`. Values below this threshold correspond to papers that share general vocabulary but not a focused research topic.
- The threshold is stored in the `similarityThreshold` property of each instance, making the decision traceable and reproducible.

## Alignment with External Sources

The `owl:sameAs` property from the OWL standard is used to link local entities to their equivalents in SemOpenAlex. This property is **not defined in this ontology**: it is a W3C standard property that is reused directly when generating RDF triples.

The following classes will have `owl:sameAs` links generated during the enrichment pipeline:

- `Paper` → linked to the corresponding SemOpenAlex work URI
- `Person` → linked to the corresponding SemOpenAlex author URI
- `Organization` → linked to the corresponding SemOpenAlex institution URI

Example of a generated triple:

```turtle
<http://kg.sports-injuries.org/paper/W2741809807>
    owl:sameAs <https://semopenalex.org/work/W2741809807> .
```

The `openAlexId` data property stored in `Paper` and `Organization` is used to construct these URIs programmatically during the pipeline.

## External Enrichment

The ontology is enriched from two distinct external sources:

- **SemOpenAlex** (RDF/SPARQL): Primary source for paper metadata, authors, affiliations, and venues. Entities are linked via `owl:sameAs`. SPARQL endpoint: `https://semopenalex.org/sparql`.

- **OpenAIRE** (REST API): Source for project and funding information, and for externally assigned keywords stored in `externalKeyword`. API documentation: `https://graph.openaire.eu/docs/apis/home/`.

> **Important distinction**: the `Topic` class and all `TopicAssignment` instances are generated **locally** by applying a topic modeling algorithm (BERTopic or LDA) on the paper abstracts. They are not imported from any external source. External keywords from OpenAIRE are stored separately in `externalKeyword` and are never used as `Topic` instances.