#!/usr/bin/env python3
"""Upload fx_rates.csv to Neon PostgreSQL, upsert on conflict."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DDL = """
CREATE TABLE IF NOT EXISTS fx_rates (
    id            BIGSERIAL    PRIMARY KEY,
    bank          VARCHAR(10)  NOT NULL,
    rate_date     DATE         NOT NULL,
    currency      VARCHAR(100) NOT NULL,
    currency_code VARCHAR(10)  NOT NULL,
    tt_buy        NUMERIC(14, 4),
    tt_sell       NUMERIC(14, 4),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT fx_rates_unique UNIQUE (bank, rate_date, currency_code)
);

CREATE INDEX IF NOT EXISTS idx_fx_rates_bank_date ON fx_rates (bank, rate_date);
CREATE INDEX IF NOT EXISTS idx_fx_rates_date       ON fx_rates (rate_date DESC);
"""

UPSERT = """
INSERT INTO fx_rates (bank, rate_date, currency, currency_code, tt_buy, tt_sell, updated_at)
VALUES %s
ON CONFLICT (bank, rate_date, currency_code) DO UPDATE SET
    currency   = EXCLUDED.currency,
    tt_buy     = EXCLUDED.tt_buy,
    tt_sell    = EXCLUDED.tt_sell,
    updated_at = EXCLUDED.updated_at
"""

STATS_QUERY = """
SELECT
    bank,
    COUNT(*)                  AS total_rows,
    COUNT(DISTINCT rate_date) AS unique_dates,
    MIN(rate_date)::text      AS earliest,
    MAX(rate_date)::text      AS latest
FROM fx_rates
GROUP BY bank
ORDER BY bank
"""


def safe_float(val) -> Optional[float]:
    try:
        f = float(str(val).replace(",", ""))
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set.", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(__file__).resolve().parent.parent / "banks" / "fx_rates.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path, dtype=str).fillna("")
    df.columns = [c.strip() for c in df.columns]
    print(f"Loaded {len(df)} rows from CSV.")

    now = datetime.now(timezone.utc)
    rows = []
    seen = set()
    for _, r in df.iterrows():
        bank = r["Bank"].strip().upper()
        rate_date = r["Date"].strip()
        currency = r["Currency"].strip()
        code = r["Currency Code"].strip().upper()
        if not bank or not rate_date or not code:
            continue
        key = (bank, rate_date, code)
        if key in seen:
            continue
        seen.add(key)
        rows.append((bank, rate_date, currency, code,
                     safe_float(r["TT Buy"]), safe_float(r["TT Sell"]), now))

    print(f"Upserting {len(rows)} rows into Neon...")

    with psycopg2.connect(db_url) as conn:
        # Create table / indexes if they don't exist
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()

        # Upsert in batches of 500
        batch_size = 500
        total_affected = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            with conn.cursor() as cur:
                execute_values(cur, UPSERT, batch)
                affected = cur.rowcount
                total_affected += affected if affected >= 0 else len(batch)
        conn.commit()

        # Collect per-bank stats from DB
        with conn.cursor() as cur:
            cur.execute(STATS_QUERY)
            stats_rows = cur.fetchall()

    bank_stats = {
        row[0]: {
            "total_rows": row[1],
            "unique_dates": row[2],
            "earliest": row[3],
            "latest": row[4],
        }
        for row in stats_rows
    }

    result = {
        "upserted": total_affected,
        "total_csv_rows": len(df),
        "bank_stats": bank_stats,
        "run_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Write stats for downstream steps (email, etc.)
    out = Path("/tmp/neon_stats.json")
    out.write_text(json.dumps(result, indent=2))

    print(f"\nUpserted {total_affected} rows. Stats:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
