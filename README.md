# Sports Injuries Scholarly Knowledge Graph

This repository contains the materials for the **Open Science and AI in Research Software Engineering** group assignment.

The project aims to build a **Scholarly Knowledge Graph** for exploring scientific literature about sports-related lower-limb injuries, including injuries affecting the foot, ankle, knee and lower-limb muscles.

## Current Deliverable

This repository includes the materials required for the ontology definition deliverable:

- Use case description
- Selected external sources
- Ontology description
- First version of the ontology diagram
- Deliverable file with the required GitHub links

## Use Case

The proposed application is a literature exploration tool based on a Scholarly Knowledge Graph. It will allow users to search and navigate scientific papers about lower-limb sports injuries by connecting papers with injuries, body parts, treatments, authors, organizations, projects and topics.

The system is **not intended to provide medical diagnosis or clinical recommendations**. Its purpose is to support the exploration of scientific knowledge in sports medicine.

The application will help answer questions such as:

- Which papers study injuries affecting a specific body part, such as the knee, ankle or foot?
- Which injury types are most frequently associated with each body part?
- Which treatment or rehabilitation methods are described for a given injury?
- Which papers are similar to a selected article?
- Which authors and organizations are most active in a specific injury area?
- Which topics emerge from the selected corpus of scientific papers?

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

The project will use two main external sources:

| Source | Type | Purpose |
|---|---|---|
| OpenAlex | REST API | Retrieve metadata about papers, authors, organizations, venues and publication years |
| SemOpenAlex | SPARQL/RDF | Link selected scholarly entities to RDF resources and query OpenAlex data as a knowledge graph |

OpenAlex will provide the initial metadata for the corpus of scientific papers. SemOpenAlex will be used to enrich and align the local Scholarly Knowledge Graph with external RDF resources.

## Repository Structure

```text
docs/
  use_case.md
  sources.md
  ontology.md
  ontology_diagram.mmd

data/
  raw_papers/
    README.md
  metadata/
    papers.csv

deliverable_ontology.txt
```

## Initial Corpus

At this stage, the repository will contain an initial subset of 11 open-access papers related to sports injuries of the lower limb.

Their bibliographic metadata will be documented in:

```text
data/metadata/papers.csv
```

For the final version of the assignment, the corpus will be expanded to 30 papers, following the scope defined in this use case.

## Group Members

- Esteban Moreno Mendoza
- Ignacio Diaz 
- Mendo Urraca Torrijos
- Juan Manuel Novoa Guevara

## License

This repository is released under the MIT License.
