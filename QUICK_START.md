# Quick Start

**Goal**: 新規ProjectをAI Collaboration Platform上で開始する

---

## Step 1: Copy

本Packの内容を対象Project Rootへコピーします。

既存Projectへ適用する場合は、同名ファイルの上書き前に差分を確認してください。

---

## Step 2: Create Project Documents

`templates/project/`から次をProject固有文書として作成します。

1. `PROJECT_CONTEXT_TEMPLATE.md`
2. `PROJECT_CHARTER_TEMPLATE.md`
3. `PROJECT_BOUNDARY_TEMPLATE.md`
4. `PROJECT_REQUIREMENTS_TEMPLATE.md`
5. `PROJECT_DEFINITION_OF_DONE_TEMPLATE.md`
6. `PHASE_KICKOFF_TEMPLATE.md`
7. `READING_ORDER_TEMPLATE.md`
8. `INTAKE_GATE_TEMPLATE.md`

推奨配置:

```text
docs/
└── project/
    ├── project_context.md
    ├── project_charter.md
    ├── project_boundary.md
    ├── project_requirements.md
    ├── definition_of_done.md
    └── phases/
        └── <phase_id>/
```

---

## Step 3: Customize AGENTS.md

`AGENTS.md`の`Project Customization`へ次を記載します。

- Project Name
- Current Phase
- Mandatory Reading
- Write Scope
- Project-specific Stop Conditions
- Project-specific Contracts

---

## Step 4: Validate Intake

`INTAKE_GATE_TEMPLATE.md`をProject用に複製し、必須文書・バックアップ・Rollback・権限を確認します。

---

## Step 5: Create Work Tasks

Task作成時は以下を使います。

- Implementation:
  `runtime/work/task_creation/implementation_task_creation_prompt_v0_9.md`
- Project Core Review:
  `runtime/work/task_creation/project_core_review_task_creation_prompt_v0_9.md`

Task名はWork UIで変更可能な場合、Task Naming Conventionに従って変更します。

---

## Step 6: Start Runtime

Implementation Taskは次を実行します。

```text
Project Understanding
  ↓
Intake Gate
  ↓
As-Is Inventory
  ↓
To-Be Design
  ↓
Implementation
  ↓
Unit Review
  ↓
Project Core Gate
  ↓
Next Work Package
```

---

## Step 7: Human Participation

Humanが介入するのは、原則として次だけです。

- Charter / Governance / Boundary / DoD変更
- Project Scope変更
- Source-of-Truth変更
- 機能減少の受容
- Rollback不能
- Formal Close
- 既存ルールでは解決できない価値判断

---

## Project Customization Notice

> このQuick StartはPlatform標準です。  
> Project固有のセットアップ手順が必要な場合は、Project RootのREADMEまたはProject固有Runbookへ追加してください。
