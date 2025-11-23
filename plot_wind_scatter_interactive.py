from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import plotly.graph_objects as go
import plotly.io as pio

# 方位を東=0度起点で定義（反時計回り）
DIRECTION_DEGREES: Dict[str, float] = {
    "東": 0.0,
    "東北東": 22.5,
    "北東": 45.0,
    "北北東": 67.5,
    "北": 90.0,
    "北北西": 112.5,
    "北西": 135.0,
    "西北西": 157.5,
    "西": 180.0,
    "西南西": 202.5,
    "南西": 225.0,
    "南南西": 247.5,
    "南": 270.0,
    "南南東": 292.5,
    "南東": 315.0,
    "東南東": 337.5,
}

STATUS_STYLE: Dict[str, Tuple[str, str]] = {
    "operational": ("circle", "#1f77b4"),
    "canceled": ("x", "#d62728"),
    "unknown": ("cross", "#7f7f7f"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plotlyで風速ベクトル散布図をHTML出力します。")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/aogashima_ship_arrivals_clean.csv"),
        help="clean_aogashima_data.py が出力したCSVパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plots/wind_scatter_interactive.html"),
        help="保存先HTMLパス",
    )
    return parser.parse_args()


def iter_vectors(input_path: Path) -> Iterable[Tuple[str, float, float]]:
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("to_aogashima_status", "unknown")
            direction = row.get("max_wind_direction", "").strip()
            speed_str = row.get("max_wind_speed_mps", "").strip()
            if not direction or not speed_str:
                continue
            if direction not in DIRECTION_DEGREES:
                continue
            try:
                speed = float(speed_str)
            except ValueError:
                continue

            theta = math.radians(DIRECTION_DEGREES[direction])
            x = speed * math.cos(theta)  # 東西成分
            y = speed * math.sin(theta)  # 南北成分
            yield status, x, y


def build_traces(vectors: Iterable[Tuple[str, float, float]]) -> List[go.Scatter]:
    buckets: Dict[str, List[Tuple[float, float]]] = {k: [] for k in STATUS_STYLE}
    for status, x, y in vectors:
        buckets.get(status, buckets["unknown"]).append((x, y))

    traces: List[go.Scatter] = []
    for status, points in buckets.items():
        xs, ys = zip(*points) if points else ([], [])
        marker_symbol, color = STATUS_STYLE[status]
        traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers",
                name=status,
                marker=dict(symbol=marker_symbol, color=color, size=8, line=dict(width=1, color="#000")),
                showlegend=True,
            )
        )
    return traces


def make_figure(traces: List[go.Scatter]) -> go.Figure:
    fig = go.Figure(data=traces)
    fig.update_layout(
        title="最大風速ベクトルの散布図（運航ステータス別）",
        xaxis_title="東西成分 (m/s, +が東)",
        yaxis_title="南北成分 (m/s, +が北)",
        xaxis=dict(zeroline=True, zerolinewidth=1, zerolinecolor="#000", showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
        yaxis=dict(zeroline=True, zerolinewidth=1, zerolinecolor="#000", showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        width=800,
        height=800,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)  # 正方座標
    return fig


def wrap_with_checkboxes(fig_html: str, output_path: Path) -> None:
    # チェックボックスで各traceをON/OFF
    template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>最大風速ベクトル散布図</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 16px; }}
    .controls {{ margin-bottom: 12px; }}
    label {{ margin-right: 12px; }}
  </style>
</head>
<body>
  <h1 style="margin-top:0;">最大風速ベクトル散布図</h1>
  <div class="controls">
    <label><input type="checkbox" data-trace="operational" checked> operational</label>
    <label><input type="checkbox" data-trace="canceled" checked> canceled</label>
    <label><input type="checkbox" data-trace="unknown" checked> unknown</label>
  </div>
  {fig_html}
  <script>
    const traceIndex = {{ operational: 0, canceled: 1, unknown: 2 }};
    const plot = document.getElementById("wind-scatter");
    const updateVisibility = () => {{
      const vis = Array(plot.data.length).fill(false);
      document.querySelectorAll('input[data-trace]').forEach(cb => {{
        if (cb.checked) {{
          const idx = traceIndex[cb.dataset.trace];
          vis[idx] = true;
        }}
      }});
      Plotly.restyle(plot, 'visible', vis);
    }};
    document.querySelectorAll('input[data-trace]').forEach(cb => cb.addEventListener('change', updateVisibility));
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding="utf-8")
    print(f"Saved: {output_path}")


def main() -> None:
    args = parse_args()
    vectors = iter_vectors(args.input)
    traces = build_traces(vectors)
    fig = make_figure(traces)
    fig_html = pio.to_html(fig, include_plotlyjs="cdn", full_html=False, div_id="wind-scatter")
    wrap_with_checkboxes(fig_html, args.output)


if __name__ == "__main__":
    main()
