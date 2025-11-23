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

## バリデーションとクレンジング

可視化・分析前に、日時やステータス、風速表記を整形したクレンジング済みCSVを作成できます。

```bash
uv run python clean_aogashima_data.py
```

`data/aogashima_ship_arrivals_clean.csv` が出力され、以下のカラムが含まれます。

- `date`: ISO形式の日付（YYYY-MM-DD）
- `weekday`: 日本語の曜日記号
- `to_aogashima_status`, `from_aogashima_status`: `operational` / `canceled` / `unknown`
- `to_aogashima_operational`, `from_aogashima_operational`: 運航=1、欠航=0、不明は空欄
- `max_wind_direction`: 方位のみを抽出
- `max_wind_speed_mps`: 風速（m/s）の数値

欠損・不正なステータスや、`max_wind` に含まれる余分な括弧の検出数は実行結果として表示されます。

## 最大風速の散布図を描く

クレンジング済みCSVを東西・南北のベクトル成分に分解し、運航ステータス別にマーカーを変えた散布図を描画できます。

```bash
uv run python plot_wind_scatter_interactive.py
```

`plots/wind_scatter_interactive.html` が生成され、ブラウザで開くと `operational` / `canceled` / `unknown` をチェックボックスで制御できます。X軸は東西（+が東）、Y軸は南北（+が北）方向の風速成分です。

- 「月」セレクトで、全期間（all）または特定の月（1〜12月）のデータに絞り込めます（シーズナリティ確認用）。
