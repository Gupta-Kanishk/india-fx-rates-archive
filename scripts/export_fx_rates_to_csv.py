#!/usr/bin/env python3
"""Export archived FX rate files into a consolidated CSV file."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup

CSV_COLUMNS = ["Bank", "Date", "Currency", "Currency Code", "TT Buy", "TT Sell"]
DATE_PATTERN = re.compile(r"(?<!\d)(\d{2})[-/](\d{2})[-/](\d{4})(?!\d)")
FILENAME_DATE_PATTERN = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")
TT_BUY_PATTERN = re.compile(r"tt\s*buy|t\.t\.?\s*buy|tt\s*buying|t\.t\.?\s*buying", re.I)
TT_SELL_PATTERN = re.compile(r"tt\s*sell|t\.t\.?\s*sell|tt\s*selling|t\.t\.?\s*selling", re.I)

CURRENCY_NORMALIZATION: Dict[str, Tuple[str, str]] = {
    "usd": ("US Dollar", "USD"),
    "us dollar": ("US Dollar", "USD"),
    "eur": ("Euro", "EUR"),
    "euro": ("Euro", "EUR"),
    "gbp": ("British Pound", "GBP"),
    "british pound": ("British Pound", "GBP"),
    "jpy": ("Japanese Yen", "JPY"),
    "japanese yen": ("Japanese Yen", "JPY"),
    "aud": ("Australian Dollar", "AUD"),
    "australian dollar": ("Australian Dollar", "AUD"),
    "cad": ("Canadian Dollar", "CAD"),
    "canadian dollar": ("Canadian Dollar", "CAD"),
    "sgd": ("Singapore Dollar", "SGD"),
    "singapore dollar": ("Singapore Dollar", "SGD"),
    "inr": ("Indian Rupee", "INR"),
    "indian rupee": ("Indian Rupee", "INR"),
    "cny": ("Chinese Yuan", "CNY"),
    "chinese yuan": ("Chinese Yuan", "CNY"),
    "nzd": ("New Zealand Dollar", "NZD"),
    "new zealand dollar": ("New Zealand Dollar", "NZD"),
    "aed": ("UAE Dirham", "AED"),
    "uae dirham": ("UAE Dirham", "AED"),
    "chf": ("Swiss Franc", "CHF"),
    "swiss franc": ("Swiss Franc", "CHF"),
    "dkk": ("Danish Krone", "DKK"),
    "danish krone": ("Danish Krone", "DKK"),
    "hkd": ("Hong Kong Dollar", "HKD"),
    "hong kong dollar": ("Hong Kong Dollar", "HKD"),
}


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def format_date(text: str) -> Optional[str]:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    day, month, year = match.groups()
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except ValueError:
        return None


def extract_date_from_filename(path: Path) -> Optional[str]:
    match = FILENAME_DATE_PATTERN.search(path.name)
    if not match:
        return None
    year, month, day = match.groups()
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except ValueError:
        return None


def extract_date_from_pdf(pdf_path: Path) -> Optional[str]:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:2]:
                text = page.extract_text() or ""
                date = format_date(text)
                if date:
                    return date
    except Exception as exc:
        print(f"Warning: unable to read date from PDF {pdf_path}: {exc}")
    return extract_date_from_filename(pdf_path)


def extract_date_from_html(html_path: Path) -> Optional[str]:
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    return format_date(text) or extract_date_from_filename(html_path)


def canonical_currency(text: str) -> Tuple[str, str]:
    key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if not key:
        return "", ""

    if key in CURRENCY_NORMALIZATION:
        return CURRENCY_NORMALIZATION[key]

    tokens = key.split()
    if tokens and len(tokens[-1]) == 3 and tokens[-1].isalpha():
        code = tokens[-1].upper()
        if code in {pair[1] for pair in CURRENCY_NORMALIZATION.values()}:
            return CURRENCY_NORMALIZATION.get(code.lower(), (code, code))
        return (code, code)

    for token, pair in CURRENCY_NORMALIZATION.items():
        if token in key:
            return pair

    return text.strip(), ""


def currency_name_and_code(value: str, fallback_code: Optional[str] = None) -> Tuple[str, str]:
    text = normalize_cell(value)
    if not text:
        return "", fallback_code or ""

    name = text
    code = None

    match = re.search(r"\(([^)]+)\)", text)
    if match:
        code = match.group(1).strip().upper()
        name = re.sub(r"\s*\([^)]*\)", "", text).strip()

    if code is None and "/" in text:
        code_candidate = text.split("/")[0].strip().upper()
        if code_candidate.isalpha():
            code = code_candidate
            name = code_candidate

    if code is None and text.upper().isalpha() and len(text) <= 4:
        code = text.upper()
        name = text

    if code is None:
        words = text.split()
        if words and words[-1].isalpha() and len(words[-1]) <= 4:
            code = words[-1].upper()
            name = " ".join(words[:-1]).strip() or code

    if code is None and fallback_code:
        code = fallback_code.upper()

    canonical_name, canonical_code = canonical_currency(name)
    if canonical_code:
        return canonical_name, canonical_code

    if code:
        return canonical_currency(code)

    return text, fallback_code or ""


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


def parse_html_table_rows(html_path: Path) -> List[List[str]]:
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    best_table = None
    best_score = -1

    for table in tables:
        rows = []
        for tr in table.find_all("tr"):
            cells = [normalize_cell(cell.get_text(separator=" ", strip=True)) for cell in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(cells)
        if not rows:
            continue
        score = sum(1 for cell in sum(rows[:2], []) if TT_BUY_PATTERN.search(cell) or TT_SELL_PATTERN.search(cell))
        if score > best_score:
            best_score = score
            best_table = rows

    return best_table or []


def parse_pdf_table_rows(pdf_path: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:2]:
                for table in page.extract_tables() or []:
                    cleaned: List[List[str]] = []
                    for row in table:
                        if not row or not any(cell and str(cell).strip() for cell in row):
                            continue
                        cleaned.append([normalize_cell(cell) for cell in row])
                    if cleaned:
                        rows = cleaned
                        break
                if rows:
                    break
    except Exception as exc:
        print(f"Warning: unable to read PDF {pdf_path}: {exc}")
    return rows


def find_column_index(header: List[str], pattern: re.Pattern) -> Optional[int]:
    for index, value in enumerate(header):
        if pattern.search(value or ""):
            return index
    return None


def rows_to_dataframe(rows: List[List[str]], date: str) -> pd.DataFrame:
    if len(rows) < 2:
        return pd.DataFrame(columns=CSV_COLUMNS)

    header_row = rows[0]
    tt_buy_index = find_column_index(header_row, TT_BUY_PATTERN)
    tt_sell_index = find_column_index(header_row, TT_SELL_PATTERN)
    currency_index = next((i for i, value in enumerate(header_row) if re.search(r"currency", value or "", re.I)), 0)
    if tt_buy_index is None or tt_sell_index is None:
        return pd.DataFrame(columns=CSV_COLUMNS)

    records = []
    for row in rows[1:]:
        if len(row) <= max(currency_index, tt_buy_index, tt_sell_index):
            continue
        currency, code = currency_name_and_code(row[currency_index])
        tt_buy = normalize_cell(row[tt_buy_index])
        tt_sell = normalize_cell(row[tt_sell_index])
        if not currency or (not tt_buy and not tt_sell):
            continue
        records.append((date, currency, code, tt_buy, tt_sell))

    return pd.DataFrame(records, columns=["Date", "Currency", "Currency Code", "TT Buy", "TT Sell"])


def parse_hdfc(bank_dir: Path) -> Optional[pd.DataFrame]:
    pdf_file = find_latest_archive_file(bank_dir, ["pdf"])
    if not pdf_file:
        return None

    rows = parse_pdf_table_rows(pdf_file)
    if len(rows) < 2:
        return None

    date = extract_date_from_pdf(pdf_file) or format_date(rows[0][0] if rows[0] else "")
    header_row = next((row for row in rows if any(re.search(r"currency", normalize_cell(cell), re.I) for cell in row)), None)
    if not header_row:
        return None

    tt_buy_index = find_column_index(header_row, TT_BUY_PATTERN)
    tt_sell_index = find_column_index(header_row, TT_SELL_PATTERN)
    if tt_buy_index is None or tt_sell_index is None:
        return None

    data_start = rows.index(header_row) + 1
    records = []
    for row in rows[data_start:]:
        if len(row) <= max(tt_buy_index, tt_sell_index):
            continue
        currency, code = currency_name_and_code(row[0], fallback_code=row[1] if len(row) > 1 else "")
        tt_buy = normalize_cell(row[tt_buy_index])
        tt_sell = normalize_cell(row[tt_sell_index])
        if not currency or (not tt_buy and not tt_sell):
            continue
        records.append((date, currency, code, tt_buy, tt_sell))

    return pd.DataFrame(records, columns=["Date", "Currency", "Currency Code", "TT Buy", "TT Sell"]) if records else None


def parse_sbi(bank_dir: Path) -> Optional[pd.DataFrame]:
    pdf_file = find_latest_archive_file(bank_dir, ["pdf"])
    if not pdf_file:
        return None

    rows = parse_pdf_table_rows(pdf_file)
    if len(rows) < 2:
        return None

    date = extract_date_from_pdf(pdf_file)
    header_row = rows[0]
    tt_buy_index = find_column_index(header_row, TT_BUY_PATTERN)
    tt_sell_index = find_column_index(header_row, TT_SELL_PATTERN)
    currency_index = next((i for i, value in enumerate(header_row) if re.search(r"currency", value or "", re.I)), 0)
    code_index = 1 if len(header_row) > 1 else currency_index
    if tt_buy_index is None or tt_sell_index is None:
        return None

    records = []
    for row in rows[1:]:
        if len(row) <= max(currency_index, tt_buy_index, tt_sell_index):
            continue
        currency, code = currency_name_and_code(row[currency_index], fallback_code=row[code_index] if len(row) > code_index else "")
        tt_buy = normalize_cell(row[tt_buy_index])
        tt_sell = normalize_cell(row[tt_sell_index])
        if not currency or (not tt_buy and not tt_sell):
            continue
        records.append((date, currency, code, tt_buy, tt_sell))

    return pd.DataFrame(records, columns=["Date", "Currency", "Currency Code", "TT Buy", "TT Sell"]) if records else None


def parse_icici(bank_dir: Path) -> Optional[pd.DataFrame]:
    html_file = find_latest_archive_file(bank_dir, ["html"])
    if not html_file:
        return None

    rows = parse_html_table_rows(html_file)
    if len(rows) < 3:
        return None

    date = extract_date_from_html(html_file)
    header_row = rows[1]
    first_data = rows[2]
    if len(header_row) + 1 == len(first_data) and TT_BUY_PATTERN.search(header_row[0]):
        header_row = [""] + header_row

    tt_buy_index = find_column_index(header_row, TT_BUY_PATTERN)
    tt_sell_index = find_column_index(header_row, TT_SELL_PATTERN)
    if tt_buy_index is None or tt_sell_index is None:
        return None

    records = []
    for row in rows[2:]:
        if len(row) <= max(tt_buy_index, tt_sell_index):
            continue
        currency, code = currency_name_and_code(row[0])
        tt_buy = normalize_cell(row[tt_buy_index])
        tt_sell = normalize_cell(row[tt_sell_index])
        if not currency or (not tt_buy and not tt_sell):
            continue
        records.append((date, currency, code, tt_buy, tt_sell))

    return pd.DataFrame(records, columns=["Date", "Currency", "Currency Code", "TT Buy", "TT Sell"]) if records else None


def parse_iob(bank_dir: Path) -> Optional[pd.DataFrame]:
    html_file = find_latest_archive_file(bank_dir, ["html"])
    if not html_file:
        return None

    rows = parse_html_table_rows(html_file)
    if len(rows) < 3:
        return None

    date = extract_date_from_html(html_file)
    rate_header = rows[1]
    first_data = rows[2]
    if len(rate_header) + 2 == len(first_data) and re.search(r"unit", rows[0][0] if rows[0] else "", re.I):
        rate_header = ["", ""] + rate_header

    tt_buy_index = find_column_index(rate_header, TT_BUY_PATTERN)
    tt_sell_index = find_column_index(rate_header, TT_SELL_PATTERN)
    currency_index = next((i for i, value in enumerate(rows[0]) if re.search(r"currency", value or "", re.I)), 1)
    if tt_buy_index is None or tt_sell_index is None:
        return None

    records = []
    for row in rows[2:]:
        if len(row) <= max(currency_index, tt_buy_index, tt_sell_index):
            continue
        currency, code = currency_name_and_code(row[currency_index])
        tt_buy = normalize_cell(row[tt_buy_index])
        tt_sell = normalize_cell(row[tt_sell_index])
        if not currency or (not tt_buy and not tt_sell):
            continue
        records.append((date, currency, code, tt_buy, tt_sell))

    return pd.DataFrame(records, columns=["Date", "Currency", "Currency Code", "TT Buy", "TT Sell"]) if records else None


def extract_bank_rates(bank: str, bank_dir: Path) -> Optional[pd.DataFrame]:
    parser = {
        "hdfc": parse_hdfc,
        "sbi": parse_sbi,
        "icici": parse_icici,
        "iob": parse_iob,
    }.get(bank)
    if not parser:
        return None
    df = parser(bank_dir)
    if df is not None and not df.empty:
        df.insert(0, "Bank", bank.upper())
        return df

    html_file = find_latest_archive_file(bank_dir, ["html"])
    if html_file:
        rows = parse_html_table_rows(html_file)
        if rows:
            fallback = rows_to_dataframe(rows, extract_date_from_html(html_file) or "")
            if not fallback.empty:
                fallback.insert(0, "Bank", bank.upper())
                return fallback

    pdf_file = find_latest_archive_file(bank_dir, ["pdf"])
    if pdf_file:
        rows = parse_pdf_table_rows(pdf_file)
        if rows:
            fallback = rows_to_dataframe(rows, extract_date_from_pdf(pdf_file) or "")
            if not fallback.empty:
                fallback.insert(0, "Bank", bank.upper())
                return fallback

    return None


def merge_with_existing_data(output_file: Path, new_data: pd.DataFrame) -> pd.DataFrame:
    if output_file.exists():
        existing = pd.read_csv(output_file, dtype=str)
        combined = pd.concat([existing, new_data], ignore_index=True)
    else:
        combined = new_data.copy()

    combined["Bank"] = combined["Bank"].astype(str).str.upper()
    combined["Currency Code"] = combined["Currency Code"].astype(str).str.upper()

    combined = combined.drop_duplicates(subset=["Bank", "Date", "Currency Code", "Currency"], keep="last")
    combined = combined.sort_values(by=["Date", "Bank", "Currency Code"], ascending=[False, True, True])
    return combined.reset_index(drop=True)


def export_csv(bank_root: Path, output_file: Path) -> None:
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
        raise RuntimeError("No bank rates could be extracted into CSV.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    combined = merge_with_existing_data(output_file, pd.concat(results.values(), ignore_index=True))
    combined.to_csv(output_file, index=False)
    print(f"Saved CSV file: {output_file}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    bank_root = script_dir.parent / "banks"
    output_file = bank_root / "fx_rates.csv"

    export_csv(bank_root, output_file)


if __name__ == "__main__":
    main()
