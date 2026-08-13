# Garmin Running Data Normalizer — 日本語案内

このファイルは、初めて利用する方向けの短い日本語入口です。仕様や契約の
正本は、英語の [`README.md`](README.md) とリンク先のProduct文書です。

現行の安定版は **v1.3.3** です。[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/latest)と
[Production PyPI](https://pypi.org/project/garmin-running-data-normalizer/)で公開済みです。
Versionや変更履歴の正本は英語のREADMEとRelease Notesを確認してください。

## 何をするOSSか

Garmin Account Exportをローカルで読み取り、再利用しやすい正規化データと
分析用のコンテキストを生成するPython CLIです。Exportや生成結果を、この
プロダクトが外部サービスへ自動送信することはありません。

## 何が得られるか

- 正規化データ
- QA、監査、来歴のエビデンス
- 同じ対応入力から再現可能な決定的出力
- 推測ではなく、明示された関係性の境界
- 人とAIの双方が読める分析ハンドオフ

対応データセット、粒度、安定キーの現在値は
[Supported Datasets](docs/supported_datasets.md)、出力の正規契約は
[Run-All Output Contract](docs/output_contract.md)を参照してください。

## 実データなしで試す

Garminアカウントを使わず、リポジトリ内のSynthetic fixtureだけで実行できます。
[Product Quick Start](docs/product_quick_start.md)の手順から始めてください。
生成結果のイメージは英語READMEの[See the result](README.md#see-the-result)で
確認できます。表示される画像と例はすべてSynthetic / fictional dataです。

Synthetic Quick Startを完了できた場合は、個人Garminデータを含めずに
[Synthetic Validation Report](https://github.com/tsubotti63/garmin-running-data-normalizer/issues/new?template=synthetic_validation_report.yml)
から結果を共有できます。

## Garmin Exportから始める

実際のExportを使う場合は、先にSynthetic workflowで導入を確認し、その後
[Getting Started from Garmin Export](docs/getting_started_from_garmin_export.md)
へ進んでください。入力と出力はローカルに置き、出力先には新しいディレクトリを
指定します。

## Privacy

実データのExportと完全なRun-All出力は個人データです。GitHub、Issue、PR、
外部AIサービスへそのまま添付しないでください。詳細は
[Security and Privacy Boundary](docs/security_and_privacy_boundary.md)を確認して
ください。

## Known Limitations

未対応入力、FITの境界、Snapshot、日次指標、外部連携などの制約は
[Known Limitations](docs/known_limitations.md)に集約しています。欠損はゼロでは
なく、未解決の関係性を推測で補うこともしません。

## Zenn記事

- [フルマラソンランナーが作った、Garmin ExportをAI分析へつなぐ正規化OSS](https://zenn.dev/tsubotti63/articles/garmin-running-data-normalizer-summary)
- [Garminの日次データを1行にまとめると何が消える？——v1.3で複数観測を残した理由](https://zenn.dev/tsubotti63/articles/garmin-v1-3-source-backed-observation-contract)

## 英語の契約文書が正本です

この日本語案内は概要であり、Version、データセット一覧、CLI契約、出力契約を
複製管理しません。判断に差がある場合は、英語の [`README.md`](README.md)、
[Product documentation index](docs/README.md)、各Schema、テスト、実行時Manifestを
正本として扱ってください。
