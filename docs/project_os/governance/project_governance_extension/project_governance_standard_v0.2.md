# Project Governance Standard

## AI Collaboration Platform

**Version:** v0.2  
**Status:** Draft Standard  
**Related Proposal:** `project_governance_extension_proposal_v0.2.md`  
**Related ADR:** `adrs/adr_0003_project_governance_extension_adoption_v0.2.md`

---

# 1. Purpose

This standard defines the common governance principles that every ACP project adopting the Project Governance Extension shall follow.

It establishes reusable governance rules while allowing project-specific Governance Profiles to extend the standard where appropriate.

---

# 2. Scope

This standard applies to:

- ACP reference projects
- Open-source ACP projects
- Governance Profiles
- Operations Framework modules

---

# 3. Governance Principles

Projects shall:

1. Preserve human accountability.
2. Keep governance decisions traceable.
3. Prefer reusable operational practices.
4. Separate governance from implementation.
5. Feed reusable improvements into Platform Evolution.

---

# 4. Architectural Boundaries

| Component | Responsibility |
|-----------|----------------|
| AI Collaboration Architecture | Collaboration principles |
| Project OS | Project structure |
| Project Factory | Project initialization |
| Project Governance Extension | Continuous governance and operation |
| Platform Evolution | Standard improvement |

Governance shall not redefine architecture, project structure, or project creation responsibilities.

---

# 5. Governance Hierarchy

```text
Governance Domain
        │
        ▼
Operation Module
        │
        ▼
Operational Activities
```

- Governance Domain defines the governed area.
- Operation Module groups reusable operational capabilities.
- Operational Activities are project-level procedures.

---

# 6. Governance Requirements

Every governed project should define:

- Governance Profile
- Operational roles
- Decision records (ADR where applicable)
- Review process
- Improvement feedback path

---

# 7. Lifecycle

The canonical lifecycle is defined exclusively in:

`governance_lifecycle_guide_v0.2.md`

Other governance documents shall reference this guide instead of duplicating lifecycle definitions.

---

# 8. Compliance

A compliant project should:

- Follow this standard
- Reference the Operations Framework
- Maintain a Governance Profile
- Record significant architectural decisions through ADRs

---

# 9. Related Documents

- `adrs/adr_0003_project_governance_extension_adoption_v0.2.md`
- project_governance_extension_proposal_v0.2.md
- operations_framework_specification_v0.2.md
- governance_lifecycle_guide_v0.2.md
- [`garmin_running_data_normalizer_governance_profile_v0.2.md`](../../../../examples/garmin_running_data_normalizer/governance/garmin_running_data_normalizer_governance_profile_v0.2.md)

---

# 10. Summary

This document defines the reusable governance rules shared by all ACP projects. Project-specific governance details belong in Governance Profiles, while operational implementation belongs in the Operations Framework Specification.
