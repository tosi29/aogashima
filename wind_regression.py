from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split


STATUS_TO_LABEL = {"operational": 0, "canceled": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="風速に基づく運航・欠航のロジスティック回帰を実行します（クレンジング済みCSV用）。"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/aogashima_ship_arrivals_clean.csv"),
        help="clean_aogashima_data.py が出力したCSVパス",
    )
    parser.add_argument(
        "--route",
        choices=["to", "from"],
        default="to",
        help="対象の航路（to: 八丈島→青ヶ島, from: 青ヶ島→八丈島）",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="検証用データの割合")
    parser.add_argument("--random-state", type=int, default=42, help="データ分割の乱数シード")
    parser.add_argument(
        "--plot-output",
        type=Path,
        default=None,
        help="ロジスティック曲線とデータ点を可視化したHTMLの出力先（未指定なら plots/wind_regression_<route>.html）",
    )
    return parser.parse_args()


def load_speed_and_labels(path: Path, route: str) -> Tuple[List[float], List[int]]:
    speeds: List[float] = []
    labels: List[int] = []
    col = "to_aogashima_status" if route == "to" else "from_aogashima_status"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get(col, "unknown")
            if status not in STATUS_TO_LABEL:
                continue  # skip unknown
            speed_str = row.get("max_wind_speed_mps", "").strip()
            if not speed_str:
                continue
            try:
                speed = float(speed_str)
            except ValueError:
                continue
            speeds.append(speed)
            labels.append(STATUS_TO_LABEL[status])
    return speeds, labels


def train_and_report(speeds: List[float], labels: List[int], test_size: float, random_state: int) -> LogisticRegression:
    X = [[s] for s in speeds]
    y = labels
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print("--- ロジスティック回帰（風速のみ）---")
    print(f"テスト精度: {acc:.3f}")
    print(f"ROC-AUC: {auc:.3f}")
    print("分類レポート:")
    print(classification_report(y_test, y_pred, target_names=["operational(0)", "canceled(1)"]))

    coef = model.coef_[0][0]
    intercept = model.intercept_[0]
    print(f"モデル係数: speed={coef:.3f}, intercept={intercept:.3f}")

    # 風速ごとの欠航確率サンプル
    checkpoints = [0, 3, 5, 7, 9, 12, 15]
    probs = model.predict_proba([[c] for c in checkpoints])[:, 1]
    print("風速ごとの推定欠航確率:")
    for c, p in zip(checkpoints, probs):
        print(f"  {c:>2} m/s: {p*100:5.1f}%")

    return model


def make_plot(speeds: List[float], labels: List[int], model: LogisticRegression, output_path: Path) -> None:
    speeds_np = np.array(speeds)
    labels_np = np.array(labels)
    xmin, xmax = speeds_np.min(), speeds_np.max()
    xs = np.linspace(xmin, xmax, 200)
    probs = model.predict_proba(xs.reshape(-1, 1))[:, 1]

    op_mask = labels_np == 0
    ca_mask = labels_np == 1
    traces = [
        go.Scatter(
            x=speeds_np[op_mask],
            y=np.zeros_like(speeds_np[op_mask]),
            mode="markers",
            name="operational",
            marker=dict(color="#1f77b4", symbol="circle", opacity=0.45),
            hovertemplate="speed=%{x:.1f} m/s<br>status=operational<extra></extra>",
        ),
        go.Scatter(
            x=speeds_np[ca_mask],
            y=np.ones_like(speeds_np[ca_mask]),
            mode="markers",
            name="canceled",
            marker=dict(color="#d62728", symbol="x", opacity=0.6),
            hovertemplate="speed=%{x:.1f} m/s<br>status=canceled<extra></extra>",
        ),
        go.Scatter(
            x=xs,
            y=probs,
            mode="lines",
            name="predicted P(canceled)",
            line=dict(color="#222", width=3),
            hovertemplate="speed=%{x:.1f} m/s<br>P(canceled)=%{y:.2f}<extra></extra>",
        ),
    ]

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="風速による欠航確率（ロジスティック回帰）",
        xaxis_title="風速 (m/s)",
        yaxis_title="P(canceled)",
        yaxis=dict(range=[-0.05, 1.05]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=520,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pio.write_html(fig, file=output_path, full_html=True, include_plotlyjs="cdn")
    print(f"プロットを保存しました: {output_path}")


def main() -> None:
    args = parse_args()
    speeds, labels = load_speed_and_labels(args.input, args.route)
    if not speeds:
        raise SystemExit("有効なデータがありません（欠航/運航が確定した行と風速が必要です）。")
    model = train_and_report(speeds, labels, args.test_size, args.random_state)

    plot_path = args.plot_output or Path(f"plots/wind_regression_{args.route}.html")
    make_plot(speeds, labels, model, plot_path)


if __name__ == "__main__":
    main()
