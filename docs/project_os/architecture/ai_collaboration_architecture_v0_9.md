# AI Collaboration Architecture v0.9

> **An architecture evolved through real-world AI collaboration**

## 1. Purpose

Human・Implementation Task・Reviewer Agent・Project Core Review Taskが、共通Project Rootと共通Governanceの上で協働する参照アーキテクチャです。

---

## 2. Operating Model

```text
Human Intent
    ↓
Platform Charter
    ↓
Project Charter / Governance / Boundary / DoD
    ↓
AGENTS.md
    ↓
Phase Kickoff
    ↓
Implementation Task
    ├── Unit Review Agent
    ├── QA / Evidence
    └── Improvement
    ↓
Project Core Gate
    ↓
Project Core Review Task
    ├── PASS → Next Work Package
    ├── REWORK → Auto Fix / Resubmit
    └── HDR → Human
```

---

## 3. Knowledge Authority

Projectの知識はチャット履歴ではなく、Project Rootに置きます。

```text
Project Root
  ├── README
  ├── AGENTS
  ├── Governance
  ├── Requirements
  ├── Runtime
  ├── Contracts
  └── Evidence
```

新TaskはProject Rootを読んでContextを再構築します。

---

## 4. Responsibility Model

| Role | Responsibility |
|---|---|
| Human | Direction, values, irreversible decisions |
| Implementation Task | Build, QA, evidence, auto fix |
| Unit Review Agent | Read-only package-level review |
| Project Core Review Task | Governance, cross-artifact, phase gate |
| Platform Documents | Stable operational rules |
| Project Documents | Domain-specific rules |

---

## 5. Design Rule

自由度を無制限に与えません。  
**自由度をあらかじめ定義**し、その範囲内で自律実行します。


## 6. Continuous Governance Extension

Project initialization後の継続運営は、[`../governance/project_governance_extension/README.md`](../governance/project_governance_extension/README.md) に接続します。

```text
AI Collaboration Architecture
        ↓
Project OS / Project Factory
        ↓
Project Governance Extension
        ↓
Operational Evidence
        ↓
Platform Improvement Intake
        ↓
Platform Evolution
```

Governance Extensionは本Architectureを再定義せず、運用・保守・レビュー・改善候補の記録を標準化します。
