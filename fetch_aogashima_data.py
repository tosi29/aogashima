from __future__ import annotations

import csv
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup


BASE_URL = "https://tma.main.jp/tokai/aogashima.php?ym={ym}"
START_YEAR, START_MONTH = 2021, 3
END_YEAR, END_MONTH = 2025, 11
REQUEST_TIMEOUT = 10


@dataclass
class DailyRecord:
    date: str
    to_aogashima: str
    from_aogashima: str
    max_wind: str


def iter_year_months(start_year: int, start_month: int, end_year: int, end_month: int):
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        yield f"{year:04d}{month:02d}"
        month += 1
        if month > 12:
            month = 1
            year += 1


def parse_month(ym: str) -> List[DailyRecord]:
    url = BASE_URL.format(ym=ym)
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as response:
        html = response.read()
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")[2:]
    records: List[DailyRecord] = []
    for row in rows:
        cells = [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) < 4:
            continue
        records.append(
            DailyRecord(
                date=cells[0],
                to_aogashima=cells[1],
                from_aogashima=cells[2],
                max_wind=cells[3],
            )
        )
    return records


def collect_records() -> List[DailyRecord]:
    records: List[DailyRecord] = []
    for ym in iter_year_months(START_YEAR, START_MONTH, END_YEAR, END_MONTH):
        print(f"Fetching {ym}...", flush=True)
        try:
            monthly_records = parse_month(ym)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Failed to fetch {ym}: {exc}", file=sys.stderr)
            continue
        if monthly_records:
            records.extend(monthly_records)
        time.sleep(1)
    return records


def write_csv(records: List[DailyRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "to_aogashima", "from_aogashima", "max_wind"])
        for record in records:
            writer.writerow([record.date, record.to_aogashima, record.from_aogashima, record.max_wind])


def main():
    records = collect_records()
    write_csv(records, Path("data/aogashima_ship_arrivals.csv"))


if __name__ == "__main__":
    main()
