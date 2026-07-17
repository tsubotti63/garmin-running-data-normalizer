# Generic Reference Project

この例は、Platformを新Projectへ適用する際の最小構成を示します。

```text
README.md
AGENTS.md
docs/
  project/
    project_context.md
    project_charter.md
    project_boundary.md
    project_requirements.md
    definition_of_done.md
    phases/
      phase1_0/
        kickoff.md
        reading_order.md
        intake_gate.md
runtime/
  project_runtime_addendum.md
```

## Example Customization

- Project Name: Example Intelligence Project
- Goal: 複数Sourceを収集・整理し、日次成果物を生成
- Human Decision: Source Policy変更・公開判断
- Autonomous Scope: 取得・正規化・QA・生成・レビュー
- Project Core Gate: Source追加、構造変更、Release
