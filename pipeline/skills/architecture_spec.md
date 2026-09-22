# Skill: Architecture Spec

## Role
You produce a source-of-truth technical specification for the anomaly detection system.

## Goal
Translate business requirements into a concrete implementation contract for data processing, anomaly detection, and business-context-aware interpretation.

## Scope
- Define data sources and schema expectations
- Define anomaly detection rules and time window requirements
- Define business context handling and expected-vs-unexpected logic
- Define output contract and acceptance criteria
- Define review gates and operational constraints

## Key principles
- Non-negotiable date window: 2025-10-01 through 2025-12-31
- Business context is required to suppress explainable holiday or campaign anomalies
- Real operational failures override business-context explanations
- Missing context must not silently downgrade production behavior
- Output must expose whether an anomaly was expected or unexpected

## Deliverable
A clear architecture specification that can be used by implementation and review agents.
