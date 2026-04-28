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
| `Topic` | Topic or cluster obtained from topic modeling over the corpus. |

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

| Property | Domain | Range | Description |
|---|---|---|---|
| `belongsToTopic` | `Paper` | `Topic` | Links a paper to a topic or cluster. |
| `similarTo` | `Paper` | `Paper` | Links two papers with similar abstracts or content. |
| `acknowledges` | `Paper` | `Person` / `Organization` | Links a paper to acknowledged people or organizations. |
| `hasAuthor` | `Paper` | `Person` | Links a paper to one of its authors. |
| `authorOf` | `Person` | `Paper` | Inverse relation of `hasAuthor`. |
| `affiliatedWith` | `Person` | `Organization` | Links an author to an institution or organization. |
| `relatedToProject` | `Paper` | `Project` | Links a paper to a research project or grant. |
| `studiesInjury` | `Paper` | `Injury` | Indicates that a paper studies a specific injury. |
| `affectsBodyPart` | `Injury` | `BodyPart` | Indicates the body part affected by an injury. |
| `focusesOnBodyPart` | `Paper` | `BodyPart` | Direct shortcut relation between a paper and the body part studied. |
| `describesTreatment` | `Paper` | `TreatmentMethod` | Indicates that a paper describes or evaluates a treatment method. |
| `appliedToInjury` | `TreatmentMethod` | `Injury` | Links a treatment method to the injury it addresses. |
| `evaluatedInSport` | `Paper` | `Sport` | Links a paper to the sport context studied. |
| `publishedIn` | `Paper` | `Venue` | Links a paper to its journal or conference. |
| `reportsMeasure` | `Paper` | `ClinicalMeasure` | Links a paper to a clinical or recovery-related measure. |
| `sameAsExternal` | `Paper`, `Person`, `Organization`, `Topic` | External URI | Links a local entity to an external resource from OpenAlex or SemOpenAlex. |

## Data Properties

### Paper

| Property | Description |
|---|---|
| `title` | Title of the paper. |
| `abstractText` | Abstract of the paper. |
| `doi` | Digital Object Identifier. |
| `publicationYear` | Year of publication. |
| `paperURL` | URL of the paper. |
| `keyword` | Keywords associated with the paper. |
| `openAlexId` | OpenAlex identifier. |
| `similarityScore` | Similarity score between two papers, when available. |

### Person

| Property | Description |
|---|---|
| `name` | Full name of the person. |
| `orcid` | ORCID identifier, if available. |
| `givenName` | Given name. |
| `familyName` | Family name. |

### Organization

| Property | Description |
|---|---|
| `name` | Name of the organization. |
| `countryName` | Country where the organization is located. |
| `countryCode` | Country code. |
| `organizationType` | Type of organization, such as education, healthcare, company or research institute. |
| `openAlexId` | OpenAlex identifier for the organization, if available. |

### Project

| Property | Description |
|---|---|
| `projectName` | Name of the project or grant. |
| `grantId` | Grant identifier. |

### Topic

| Property | Description |
|---|---|
| `topicName` | Human-readable topic label. |
| `topicDescription` | Short description of the topic. |
| `topTerms` | Most representative terms of the topic. |

### BodyPart

| Property | Description |
|---|---|
| `bodyPartName` | Name of the body part. |
| `bodyRegion` | Anatomical region, for example lower limb. |
| `synonymLabel` | Alternative labels or synonyms. |

### Injury

| Property | Description |
|---|---|
| `injuryName` | Name of the injury. |
| `injuryCategory` | Category of injury, such as ligament, muscle, tendon, bone or overuse. |
| `injuryDescription` | Short textual description of the injury. |

### TreatmentMethod

| Property | Description |
|---|---|
| `treatmentName` | Name of the treatment or rehabilitation method. |
| `treatmentType` | Type of treatment, such as surgery, physiotherapy, exercise, prevention or recovery protocol. |
| `treatmentDescription` | Short description of the treatment. |

### Venue

| Property | Description |
|---|---|
| `venueName` | Name of the journal or conference. |
| `venueType` | Type of venue, for example journal or conference. |

### Sport

| Property | Description |
|---|---|
| `sportName` | Name of the sport or activity. |

### ClinicalMeasure

| Property | Description |
|---|---|
| `measureName` | Name of the clinical or recovery-related measure. |
| `measureUnit` | Unit of measurement, if applicable. |

## External Enrichment

The first version of the ontology is designed to be enriched mainly with two sources:

- `OpenAlex`, as the REST API source for paper metadata, authors, organizations, venues and topics.
- `SemOpenAlex`, as the RDF/SPARQL source for linking the local graph to external RDF resources.

The main external identifiers will be represented with `openAlexId` and `sameAsExternal`.
