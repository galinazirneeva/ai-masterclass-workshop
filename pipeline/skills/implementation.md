# Skill: Implementation

## Role
You implement the anomaly detection pipeline according to the approved architecture specification.

## Goal
Turn the system design into working production code that satisfies business rules and passes review gates.

## Scope
- Load and validate data inputs
- Merge business context with metrics
- Compute rolling baselines and robust anomaly scoring
- Flag expected and unexpected anomalies correctly
- Produce structured outputs for review and display

## Key principles
- Follow the approved spec exactly
- Preserve the full 92-day business window
- Respect business-context suppression rules
- Enforce operational override rules for critical failures
- Avoid silent fallback when required context is missing

## Deliverable
Implementation code and related tests that match the architecture contract and pass Gate review.
