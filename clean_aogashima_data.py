from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# The original CSV uses Japanese weekday symbols in parentheses.
WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
STATUS_MAP = {"〇": "operational", "○": "operational", "×": "canceled", "✕": "canceled"}
WIND_PATTERN = re.compile(r"^(?P<direction>[^\s]+)\s+(?P<speed>\d+(?:\.\d+)?)$")


@dataclass
class CleaningStats:
    total_rows: int = 0
    unknown_status_to: int = 0
    unknown_status_from: int = 0
    invalid_status_values: Dict[str, int] = field(default_factory=dict)
    max_wind_missing: int = 0
    max_wind_invalid: int = 0
    max_wind_trimmed_trailing_paren: int = 0

    def add_invalid_status(self, raw_value: str) -> None:
        key = raw_value if raw_value else "(blank)"
        self.invalid_status_values[key] = self.invalid_status_values.get(key, 0) + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and clean Aogashima ship arrival data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/aogashima_ship_arrivals.csv"),
        help="Path to the raw CSV exported by fetch_aogashima_data.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/aogashima_ship_arrivals_clean.csv"),
        help="Destination for the cleaned CSV",
    )
    return parser.parse_args()


def normalize_date(raw_date: str) -> Tuple[str, str]:
    match = re.match(r"^(?P<ymd>\d{4}/\d{2}/\d{2})\s*\((?P<weekday>.)\)$", raw_date)
    if not match:
        raise ValueError(f"Invalid date format: {raw_date}")

    date_str = match.group("ymd")
    weekday_symbol = match.group("weekday")
    parsed = datetime.strptime(date_str, "%Y/%m/%d").date()
    expected_symbol = WEEKDAY_JA[parsed.weekday()]
    weekday_to_use = expected_symbol
    if weekday_symbol != expected_symbol:
        # Keep computed weekday to guarantee consistency.
        weekday_to_use = expected_symbol
    return parsed.isoformat(), weekday_to_use


def normalize_status(raw_status: str | None, stats: CleaningStats, field: str) -> str:
    if raw_status is None or str(raw_status).strip() == "":
        if field == "to_aogashima":
            stats.unknown_status_to += 1
        else:
            stats.unknown_status_from += 1
        stats.add_invalid_status("(blank)")
        return "unknown"

    cleaned = str(raw_status).strip()
    if cleaned in STATUS_MAP:
        return STATUS_MAP[cleaned]

    if field == "to_aogashima":
        stats.unknown_status_to += 1
    else:
        stats.unknown_status_from += 1
    stats.add_invalid_status(cleaned)
    return "unknown"


def normalize_max_wind(raw_wind: str | None, stats: CleaningStats) -> Tuple[str, str]:
    if raw_wind is None or str(raw_wind).strip() == "":
        stats.max_wind_missing += 1
        return "", ""

    cleaned = str(raw_wind).strip()
    trimmed = cleaned.rstrip(" )").replace("\u3000", " ")
    trimmed = re.sub(r"\s+", " ", trimmed)
    if trimmed != cleaned:
        stats.max_wind_trimmed_trailing_paren += 1

    match = WIND_PATTERN.match(trimmed)
    if not match:
        stats.max_wind_invalid += 1
        return "", ""

    direction = match.group("direction")
    speed = f"{float(match.group('speed')):.1f}"
    return direction, speed


def read_rows(input_path: Path) -> Iterable[Dict[str, str]]:
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        yield from reader


def write_clean_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date",
        "weekday",
        "to_aogashima_status",
        "from_aogashima_status",
        "to_aogashima_operational",
        "from_aogashima_operational",
        "max_wind_direction",
        "max_wind_speed_mps",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_records(raw_rows: Iterable[Dict[str, str]], stats: CleaningStats) -> List[Dict[str, str]]:
    cleaned_rows: List[Dict[str, str]] = []
    for raw in raw_rows:
        stats.total_rows += 1
        date_iso, weekday = normalize_date(raw["date"])
        to_status = normalize_status(raw.get("to_aogashima"), stats, "to_aogashima")
        from_status = normalize_status(raw.get("from_aogashima"), stats, "from_aogashima")
        wind_dir, wind_speed = normalize_max_wind(raw.get("max_wind"), stats)

        cleaned_rows.append(
            {
                "date": date_iso,
                "weekday": weekday,
                "to_aogashima_status": to_status,
                "from_aogashima_status": from_status,
                "to_aogashima_operational": "" if to_status == "unknown" else ("1" if to_status == "operational" else "0"),
                "from_aogashima_operational": "" if from_status == "unknown" else ("1" if from_status == "operational" else "0"),
                "max_wind_direction": wind_dir,
                "max_wind_speed_mps": wind_speed,
            }
        )
    return cleaned_rows


def print_report(stats: CleaningStats, output_path: Path) -> None:
    print(f"Rows processed: {stats.total_rows}")
    print(f"Wrote cleaned data to: {output_path}")
    print("--- Validation summary ---")
    print(f"Missing/unknown to_aogashima status: {stats.unknown_status_to}")
    print(f"Missing/unknown from_aogashima status: {stats.unknown_status_from}")
    print(f"Max wind missing values: {stats.max_wind_missing}")
    print(f"Max wind invalid rows: {stats.max_wind_invalid}")
    print(f"Trailing parentheses trimmed from wind values: {stats.max_wind_trimmed_trailing_paren}")
    if stats.invalid_status_values:
        print("Status values needing attention:")
        for raw_value, count in sorted(stats.invalid_status_values.items(), key=lambda x: x[1], reverse=True):
            print(f"  {raw_value}: {count}")


def main() -> None:
    args = parse_args()
    stats = CleaningStats()
    raw_rows = read_rows(args.input)
    cleaned_rows = clean_records(raw_rows, stats)
    write_clean_csv(cleaned_rows, args.output)
    print_report(stats, args.output)


if __name__ == "__main__":
    main()
