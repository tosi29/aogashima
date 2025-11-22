# aogashima

このリポジトリには、青ヶ島航路の運航・欠航状況をまとめたCSVを生成するシンプルなスクリプトが入っています。

## データ収集

このリポジトリは [uv](https://docs.astral.sh/uv/) で構成管理しています。初めて利用する場合は依存関係を同期してください。

```bash
uv sync
```

同期後、`uv run` で `fetch_aogashima_data.py` を実行すると、2021年3月〜2025年11月の各月に対して [公開されている時刻表ページ](https://tma.main.jp/tokai/aogashima.php) から日別データを取得し、`data/aogashima_ship_arrivals.csv` に集約します。

```bash
uv run python fetch_aogashima_data.py
```

出力されるCSVのカラムは次のとおりです。

- `date`: 日付（曜日入り）
- `to_aogashima`: 八丈島発→青ヶ島行きの運航・欠航表示
- `from_aogashima`: 青ヶ島発→八丈島行きの運航・欠航表示
- `max_wind`: アメダス八丈島の最大風速（方位と数値）
