# Definition of Done Standard v0.9

## 1. Completion Layers

### Technical Complete

実装とQAが完了している。

### Operational Complete

正式な実行導線・Runbook・Monitoring・Cleanupが成立している。

### Review Complete

Unit Reviewと必要なProject Core GateがPASSしている。

### Handoff Complete

第三者Human / AIが必要資産を取得し、再開できる。

### Formal Close

Humanまたは定義済みClose Authorityが正式承認する。

---

## 2. Minimum DoD

- Scope deliverables complete
- Deterministic QA pass
- Negative paths verified
- Evidence retained
- Documentation updated
- Rollback / Recovery defined
- Project Core Gate pass where required
- Remaining limitations explicit
- Formal Close authority identified

---

## 3. Prohibited Close

次の場合はCloseしません。

- 「コードが動いた」だけ
- ローカル環境でしか再現できない
- 正式導線に統合されていない
- Evidenceがない
- Handoffに必要な資産が欠ける
- Known limitationが隠されている

---

## 4. Project Customization

Project固有の成果物・品質・Handoff・Close条件を追加してください。
