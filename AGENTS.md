# AGENTS.md

**Version**: v0.9
**Status**: Platform Standard with Project Customization
**Purpose**: AI実行環境のBoot Rules

- **Audience**: AI-assisted development tasks and maintainers
- **Not a product installation or usage guide**
- **Product behavior authority**: Product contracts, schemas, tests, and the
  stable release
- **Platform authority**: AI collaboration and review operations only

---

## 1. Authority Order

上位ほど優先します。

1. Explicit Human Decision
2. Platform Charter (`docs/project_os/governance/platform_charter_v0_9.md`)
3. Project Charter (`docs/project/project_charter.md`)
4. Project Governance (`docs/project/project_governance.md`)
5. Project Definition of Done (`docs/project/definition_of_done.md`)
6. Project Boundary (`docs/project/project_boundary.md`)
7. Current Work Package / Review Package
8. Local Runtime Rules (`runtime/project_runtime_addendum.md`)

解消不能な矛盾は`HUMAN_DECISION_REQUIRED`です。

---

## 2. Platform Standard

### Fact and Evidence

- 推測で事実を作らない
- 事実・解釈・仮説を分離する
- QA / Manifest / Inventory / Hash / 実成果物を根拠にする

### Autonomous Execution

Boundary内では自律実行します。

- `AUTO_PASS`
- `AUTO_FIX`
- `CONTINUE`
- `PROJECT_CORE_GATE`
- `HUMAN_DECISION_REQUIRED`

工程完了や進捗報告だけを理由に停止しません。

### Improvement

> **Report, Don't Stop.**

安全な改善は実装・検証・記録後に継続します。

### Review

- Implementation Taskの自己評価だけでCloseしない
- Unit Review Agentは個別成果物をread-only reviewする
- Project Core Review Taskは全体Gateを独立監査する
- PASSはNext Work Package Start Event
- REWORKはBoundary内ならAuto Fix
- Human Decisionが必要な場合だけ停止

### Output

Human向けチャット出力は日本語を基本とし、最小構成にします。

- Current Status
- Last Gate / Verdict
- Blocker
- HUMAN_DECISION_REQUIRED
- Important Evidence
- Next Action

詳細は成果物へ記録します。

---

## 3. Platform Stop Conditions

次のみ停止できます。

- 既存契約で解決できない価値判断
- Charter / Governance / Boundary / DoD変更
- Project Scope変更
- Source-of-Truth変更
- 機能減少の受容
- Rollback不能
- 外部入力がなければ継続不能
- Platform機能制約でTask Collaborationが成立しない
- Formal Close

テスト失敗・Path不整合・配置漏れ・レビューREWORKは、Boundary内で修正可能なら停止理由ではありません。

---

## 4. Project Customization

### Project Name

`GARMINデータ正規化` / `Garmin Running Data Normalizer`

### Current Phase

`Stable v1.3.2 maintenance and public-surface alignment` (release preparation)

### Mandatory Reading

1. `README.md`
2. `docs/README.md`
3. `docs/supported_datasets.md`
4. `docs/output_contract.md`
5. `docs/dataset_relationships.md`
6. `docs/known_limitations.md`
7. `docs/project/project_charter.md`, `docs/project/project_boundary.md`, and
   `docs/project/definition_of_done.md`
8. `docs/project_os/governance/platform_charter_v0_9.md` for development
   governance
9. Current Work Package / Review Package

### Responsibility Boundary

- Product contracts own Product behavior.
- ACP documents own AI-assisted development governance.
- `AGENTS.md` adapts the execution environment and must not redefine Product
  contracts.

### Authorized Write Scope

- Target repository only
- Synthetic fixtures and Git-ignored Target review evidence

Source repository, Platform repository, and supplied Platform ZIP are read-only.

### Project-specific Stop Conditions

- OSS license, Source public redistribution rights, publication, GitHub/remote,
  push/tag/release, or Open-Meteo production use-tier decision is required
- Requested work crosses the privacy boundary or reduces a confirmed safety
  property
- Rollback cannot be preserved

Boundary-local defects and Target review REWORK are自律修正します。

### Project-specific Contracts

- `docs/project/project_boundary.md`
- `docs/project/project_requirements.md`
- `docs/reference/platform_adoption.md`
- `docs/reference/reuse_matrix.md`
- `config/dataset_registry.example.json`
- `schemas/dataset_registry.schema.json`

### Project-specific Review Authority

- 全実装はTarget Implementation Taskが所有する
- Project Core GateはTarget Project Core Review roleだけが所有する
- Source task/reviewはhistorical handoff evidenceであり、active gateではない
- Target Project Core Review PASSまでcommitは禁止する

### Project-specific Output Requirements

- Human向けチャットは日本語
- Canonical code/file/contract名は英語のまま維持する
- tests、scan、Inventory、Manifest/hash、Unit Review、Blocker、次Actionを
  Review Packへ記録する
- 未実施・未確認事項を完了扱いしない

---

## 5. Customization Completion Gate

未解決の`<...>` placeholderがある場合はIntake Gateを`REWORK`とします。
