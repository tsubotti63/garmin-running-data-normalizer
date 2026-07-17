# Project Core Gate Protocol v0.9

## Gate Lifecycle

```text
GATE_PREPARE
  ↓
PACKAGE_FREEZE
  ↓
REVIEW_REQUEST_SENT
  ↓
IN_PROGRESS
  ↓
PASS / REWORK / HUMAN_DECISION_REQUIRED
  ↓
GATE_CLOSE or RESUBMIT
```

## Gate Selection

Project Core Gateは次に使用します。

- Project全体構造の変更
- Cross-artifact整合
- Architecture / Governance影響
- Major Work Package完了
- Phase Handoff
- Formal Close candidate

README修正等の局所変更を毎回Core Gateへ送らないでください。

## Package Freeze

Review中の提出Packageを改変しません。  
修正は次CycleのPackageとして再提出します。

## Verdict Processing

- PASS: Gate Close → Next Work Package
- REWORK: Boundary内Auto Fix → Unit Review → Next Cycle
- HDR: Humanへ圧縮Escalation

## Gate ID

推奨形式:

`{PHASE}-CORE-GATE-{NNN}`

例:

`P10-CORE-GATE-001`
