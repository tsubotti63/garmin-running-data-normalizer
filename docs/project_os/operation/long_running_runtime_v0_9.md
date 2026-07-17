# Long-running Runtime v0.9

## Goal

Humanが離席している間も、停止条件までWork Packageを自律継続します。

## Runtime Rule

```text
PASS → Continue
REWORK + Boundary-safe → Auto Fix → Resubmit
Review waiting → Wait / Poll / Resume
Progress report → Record, do not stop
HUMAN_DECISION_REQUIRED → Stop
Platform limit → Checkpoint and stop
```

## Checkpoint

実行単位・利用制限・Platform制約で終了する場合:

- `PLATFORM_CHECKPOINT`として分類
- Last completed Gate
- Current Work Package
- Resume command
- Modified files
- Pending review
- Integrity status

を記録します。

## Human Away Mode

Humanは外出前に開始し、外出中は次だけ確認できます。

- Current Work Package
- Last Verdict
- HDRの有無
- Platform limit
- Resume point

## Prohibited Stop

- Work Package完了
- PASS
- 通常進捗報告
- Non-blocking improvement
- Boundary内REWORK

だけを理由に停止しません。
