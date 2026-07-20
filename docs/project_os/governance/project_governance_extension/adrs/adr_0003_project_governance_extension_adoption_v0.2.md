# ADR-0003: Adopt Project Governance Extension

- **Status:** Accepted
- **Version:** v0.2
- **Date:** 2026-07

## Purpose

Record the architectural decision to adopt the Project Governance Extension as an official ACP extension.

## Background

ACP already defines:

- AI Collaboration Architecture
- Project OS
- Project Factory
- Platform Evolution

A reusable operational governance layer was missing.

## Decision

Adopt Project Governance Extension as the standard operational layer for projects after initialization.

## Architectural Position

```text
AI Collaboration Architecture
            │
       Project OS
            │
     Project Factory
            │
Project Governance Extension
            │
   Platform Evolution
```

The Governance Extension operates **beneath AI Collaboration Architecture** and **alongside Project OS**, implementing operational governance without redefining collaboration principles or project structure.

## Responsibility Matrix

| Component | Responsibility |
|---|---|
| AI Collaboration Architecture | Collaboration principles and boundaries |
| Project OS | Standard project structure |
| Project Factory | Project creation and initialization |
| Project Governance Extension | Continuous project operation and governance |
| Platform Evolution | Standardization and platform improvement |

## Governance Model

```text
Governance Domain
        │
        ▼
Operation Module
        │
        ▼
Operational Activities
```

Governance Domains define *what* is governed. Operation Modules define *how* governance is executed. Operational Activities are the concrete procedures used by projects.

## Lifecycle

The canonical lifecycle definition is maintained in:

- [`../governance_lifecycle_guide_v0.2.md`](../governance_lifecycle_guide_v0.2.md)

All other governance documents reference that guide to avoid duplicated lifecycle definitions.

## Alternatives Considered

1. Integrate governance into Project Factory — Rejected.
2. Integrate governance into Project OS — Rejected.
3. Independent ACP Extension — Accepted.

## Consequences

Benefits:

- Standardized governance
- Reusable operational patterns
- Consistent feedback into Platform Evolution

Risks:

- Documentation maintenance
- Boundary confusion if responsibilities are not maintained

## Initial Scope

Included artifacts:

- Proposal
- Standard
- Operations Framework Specification
- Governance Lifecycle Guide
- Governance Profile
- Reference Implementation

Initial Reference Implementation:

- Garmin Running Data Normalizer

## Future Evolution

Planned enhancements:

- Governance Metrics
- Security / Compliance / Automation Operations
- Additional Reference Implementations

## Review Reflection

Architectural review outcome:

- Ready
- No blockers

Implemented improvements:

- Architecture boundary clarified
- Responsibility matrix added
- Governance Domain → Operation Module relationship defined
- Lifecycle source centralized

## Decision

**Accepted**

Project Governance Extension is adopted as an official ACP extension and will evolve through reference-project experience.
