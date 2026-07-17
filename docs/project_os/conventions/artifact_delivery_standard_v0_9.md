# Artifact Delivery Standard v0.9

## Core Principle

> コピー先を説明する成果物ではなく、コピーできる成果物を渡す。

成果物はProject Root基準のディレクトリ構造で提供します。

## Example

```text
docs/
└── project_os/
    └── operation/
        └── new_standard.md
```

HumanはZIPを展開し、Project Rootへコピーします。

## AI Responsibilities

- Root-relative hierarchyを再現
- 新DirectoryにはREADMEを含める
- 大規模PackageにはManifest / Inventory / Hashを含める
- 個別配置作業をHumanへ要求しない
- 削除・移動が必要な場合はMigration Guideを含める

## Delivery Types

- Directory Update
- Subsystem Update
- Runtime Update
- Documentation Update
- Transfer Snapshot
- Full Project Handoff
