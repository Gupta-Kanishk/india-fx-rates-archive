#!/usr/bin/env python3
"""Export archived FX rate files into a consolidated Excel workbook."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def find_latest_archive_file(bank_dir: Path, extensions: List[str]) -> Optional[Path]:
    candidates = []
    for ext in extensions:
        candidates.extend(bank_dir.glob(f"*.{ext}"))

    def file_date(path: Path) -> str:
        match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
        return match.group(1) if match else path.name

    sorted_candidates = sorted(
        candidates,
        key=lambda path: (file_date(path), path.name),
        reverse=True,
    )
    return sorted_candidates[0] if sorted_candidates else None


def html_table_rows(html_path: Path) -> List[List[str]]:
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []

    target = None
    for table in tables:
        classes = table.get("class") or []
        if any("exchange-rate" in str(cls).lower() for cls in classes):
            target = table
            break
    if target is None:
        target = tables[0]

    rows = []
    for tr in target.find_all("tr"):
        cells = [normalize_cell(cell.get_text(separator=" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if any(cell for cell in cells):
            rows.append(cells)
    return rows


def pdf_rate_rows(pdf_path: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    cleaned = [
                        [normalize_cell(cell) for cell in row]
                        for row in table
                        if any(cell and str(cell).strip() for cell in row)
                    ]
                    if cleaned:
                        rows.extend(cleaned)
                if rows:
                    break

            if rows:
                return rows

            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.splitlines():
                    text_line = line.strip()
                    if not text_line:
                        continue
                    if re.search(r"\b(USD|EUR|GBP|JPY|AUD|CAD|SGD|AED|SAR|CHF|CNY)\b", text_line, flags=re.I):
                        parts = re.split(r"\s{2,}|\t|\|", text_line)
                        cleaned = [normalize_cell(part) for part in parts if normalize_cell(part)]
                        if len(cleaned) > 1:
                            rows.append(cleaned)
                if rows:
                    break
    except Exception as exc:
        print(f"Error reading PDF {pdf_path}: {exc}")
    return rows


def rows_to_dataframe(rows: List[List[str]]) -> Optional[pd.DataFrame]:
    if not rows:
        return None
    header = rows[0]
    if any("currency" in cell.lower() for cell in header if cell):
        clean_headers = [cell or f"Column{i + 1}" for i, cell in enumerate(header)]
        body = rows[1:]
        if all(len(row) == len(clean_headers) for row in body):
            return pd.DataFrame(body, columns=clean_headers)
        return pd.DataFrame(body)
    return pd.DataFrame(rows)


def extract_bank_rates(bank: str, bank_dir: Path) -> Optional[pd.DataFrame]:
    # Prefer PDF archives when available, but fall back to HTML parsing for banks
    # whose latest snapshot is stored as HTML.
    pdf_file = find_latest_archive_file(bank_dir, ["pdf"])
    if pdf_file:
        rows = pdf_rate_rows(pdf_file)
        df = rows_to_dataframe(rows)
        if df is not None and not df.empty:
            return df

    html_file = find_latest_archive_file(bank_dir, ["html"])
    if html_file:
        rows = html_table_rows(html_file)
        df = rows_to_dataframe(rows)
        if df is not None and not df.empty:
            return df

    return None


def export_workbook(bank_root: Path, output_file: Path) -> None:
    results: Dict[str, pd.DataFrame] = {}
    for bank in ["hdfc", "sbi", "icici", "iob"]:
        bank_dir = bank_root / bank
        if not bank_dir.exists():
            print(f"Skipping missing bank directory: {bank_dir}")
            continue

        print(f"Extracting rates for {bank.upper()}...")
        df = extract_bank_rates(bank, bank_dir)
        if df is None or df.empty:
            print(f"  No structured rate data found for {bank.upper()}.")
            continue

        results[bank.upper()] = df
        print(f"  Extracted {len(df)} rows for {bank.upper()}.")

    if not results:
        raise RuntimeError("No bank rates could be extracted into Excel.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for sheet_name, df in results.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)

    print(f"Saved Excel workbook: {output_file}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    bank_root = script_dir.parent / "banks"
    output_file = bank_root / "fx_rates.xlsx"

    export_workbook(bank_root, output_file)


if __name__ == "__main__":
    main()
