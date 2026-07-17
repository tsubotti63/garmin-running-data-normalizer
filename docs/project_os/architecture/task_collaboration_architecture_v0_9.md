# Task Collaboration Architecture v0.9

## 1. Purpose

独立したAI Task間で、Review Package・Gate ID・Verdictを交換し、Human Relayなしで閉ループを形成します。

---

## 2. Collaboration Flow

```text
Implementation Task
    │
    ├─ Build Review Package
    ├─ Assign Gate ID
    └─ Send Review Request
             ↓
Project Core Review Task
    │
    ├─ Validate Package
    ├─ Review Evidence
    └─ Return Verdict
             ↓
Implementation Task
    ├─ PASS → Continue
    ├─ REWORK → Auto Fix → Resubmit
    └─ HDR → Human
```

---

## 3. Message Contract

Review Requestには最低限次を含めます。

- Gate ID
- Project / Phase / Work Package
- Review Goal
- Review Package path or attachment
- Manifest
- Requested Verdict
- Return destination
- Expected next action

Review Resultには次を含めます。

- Gate ID
- Verdict
- Blocker
- Boundary result
- Important evidence
- Required rework
- Non-blocking improvement
- Next action

---

## 4. Collaboration Registry

Task Identityは表示名だけに依存しません。

推奨Registry項目:

- Logical Role
- Task Display Name
- Runtime Prompt
- Authority
- Message Route
- Current State
- Last Gate ID

---

## 5. Failure Rule

Task間直接連携が不可能な場合、Human Relayへ暗黙Fallbackしません。

Evidenceを残し、Alternative Architectureを提示して`HUMAN_DECISION_REQUIRED`とします。

---

## 6. Project Customization

使用Platformに応じたTask間送信機能・制約を記載してください。
