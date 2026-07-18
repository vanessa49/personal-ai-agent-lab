# Submission Form Copy

## Title

Dataset Design as Ontology Design: Representational Consequences of QA Segmentation in Personal AI Interaction Data

## Abstract

Personalized AI systems increasingly rely on fine-tuning language models on longitudinal interaction data. The dominant practice converts this data into question–answer (QA) pairs, thereby operationalizing interaction as locally independent query–response mappings rather than temporally structured processes. We empirically test this assumption through a longitudinal case study of a single three-year personal interaction corpus (1,122 sessions, 35,756 role-marked turns), constructing two parallel representations of the same underlying data—a cognitive trajectory graph and QA-derived pair sequences—and comparing their structural properties across six controlled conditions. We find that trajectory-based representations exhibit significantly different transition dynamics from QA-derived ones (KS D = 0.298). These differences persist under semantic reconstruction and when evaluated over the full corpus. An order-shuffled counterfactual further demonstrates that temporal ordering, rather than content alone, accounts for the observed structure (KS D = 0.101). These results show that QA slicing removes explicit supervision for higher-order conditional dependencies by collapsing multi-step sequences into independent pairs. We release a reproducible pipeline and privacy-safe aggregate evidence.

## Keywords

personal AI; longitudinal interaction; dataset representation; QA segmentation; cognitive trajectories; data-centric AI

## Contribution summary

The paper contributes a graph-based representation and controlled evaluation framework for longitudinal interaction data; a deduplicated case study showing that QA slicing collapses chain structure while retaining local semantic continuity; and methodological evidence that temporal order is a first-class property of personal-AI datasets rather than incidental metadata.

## Data and code availability

The raw multi-year conversation corpus is not released because it contains sensitive personal information. The accompanying repository provides the full processing and analysis code, synthetic sample data, aggregate paper-facing metrics, validation results, and cryptographic hashes linking the compact summary to its aggregate source files. No raw conversation text or per-item model outputs are included.

## Scope statement

This paper establishes representation-level structural differences. It does not claim that trajectory fine-tuning improves deployed model behavior, retrieval performance, or fidelity to an individual's cognition.
