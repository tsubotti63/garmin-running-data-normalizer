# Boundary and Escalation Standard v0.9

## 1. Purpose

AIの自律範囲とHumanへEscalationする条件を明確化します。

---

## 2. Default Autonomous Scope

Project Boundaryが許可する範囲で、次を自律実行できます。

- 実装・修正・Refactoring
- QA追加・修正
- Path / Import / Configuration整合
- Documentation更新
- Unit Review / Project Core Review
- Evidence生成
- 再生成可能な一時資産のCleanup
- 機能減少を伴わない改善

---

## 3. Standard Human Decision Conditions

- Project Charter変更
- Governance変更
- Boundary変更
- Definition of Done変更
- Project Scope変更
- Source-of-Truth変更
- Data Meaning / Schema Semantics変更
- 機能減少または品質低下の受容
- Rollback不能
- External legal / financial / security commitment
- Formal Close

---

## 4. Escalation Format

`HUMAN_DECISION_REQUIRED`では次だけを提示します。

1. 判断事項
2. 確認済み事実
3. 影響
4. 推奨案
5. 代替案
6. 回答後の自動再開位置

---

## 5. Non-blocking Conditions

次は通常、Human停止条件ではありません。

- Unit Review REWORK
- Project Core Review REWORK
- QA failure with known fix
- Missing README
- Hard-coded path
- Duplicate documentation
- Reproducible workspace cleanup
- Improvement opportunity

---

## 6. Project Customization

各Projectは追加の停止条件を定義してください。

```text
<PROJECT_SPECIFIC_HUMAN_DECISION_CONDITION_1>
<PROJECT_SPECIFIC_HUMAN_DECISION_CONDITION_2>
```
