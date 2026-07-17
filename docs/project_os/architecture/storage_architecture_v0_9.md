# Storage Architecture v0.9

## Principles

- Evidence is persistent
- Workspace is reproducible
- Cache is disposable
- Delivery preserves root-relative paths
- Cleanup is part of the lifecycle

## Storage Classes

| Class | Examples | Retention |
|---|---|---|
| Immutable | Original inputs, signed baseline | Never delete without authority |
| Persistent | Contracts, QA, review, closeout | Long-term |
| Candidate | Candidate outputs | Until acceptance/rejection close |
| Workspace | Temporary execution copy | Reproducible; cleanup after gate |
| Cache | Tool cache | Anytime |
| Transfer Snapshot | ZIP package | Retain according to project policy |

## Cleanup Gate

```text
Close / Checkpoint
  ↓
Cleanup Inspection
  ↓
Delete Candidates
  ↓
Capacity Report
  ↓
Integrity Recheck
```

## Project Customization

Data sensitivity・retention period・backup・external storageをProject固有に定義してください。
