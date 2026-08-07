# 🇮🇳 India FX Rates Archive

A public automated repository that **downloads, archives, and stores daily forex card / treasury FX rates** from major Indian banks — both as flat CSV files and in a managed PostgreSQL database (Neon).

## Supported Banks
- HDFC Bank
- State Bank of India (SBI)
- ICICI Bank
- Indian Overseas Bank (IOB)

## Data Sources
- HDFC: Direct PDF
- SBI: Direct PDF
- ICICI: Website rendered as PDF
- IOB: Website rendered as PDF

## Features
- 📥 Automatic daily download using GitHub Actions
- 📄 Saves source PDFs directly when available
- 🌐 Converts HTML rate pages into PDF snapshots
- 🧾 Exports parsed daily TT Buy/Sell rates into a consolidated CSV file for all 4 banks
- 🗂 Organizes files bank-wise and date-wise
- 🔁 Automatically pushes updates to GitHub
- 📚 Maintains historical FX rate archive
- 🐘 Upserts rates into **Neon PostgreSQL** (no duplicates, idempotent)
- 📊 Daily email summary with per-bank row counts, date ranges, and upsert stats

## Repository Layout
- `banks/hdfc/` — HDFC PDF archive
- `banks/sbi/` — SBI PDF archive
- `banks/icici/` — ICICI HTML + PDF archive
- `banks/iob/` — IOB HTML + PDF archive
- `banks/fx_rates.csv` — Consolidated TT Buy/Sell rates for all banks and dates
- `scripts/download_fx_rates.py` — Downloads source files and converts HTML pages to PDF
- `scripts/export_fx_rates_to_csv.py` — Parses PDFs/HTML and writes `banks/fx_rates.csv`
- `scripts/upload_to_neon.py` — Upserts CSV data into Neon PostgreSQL
- `scripts/update_repo.sh` — Runs download, commits changes, and pushes to GitHub

## Setup

### Automatic Daily Downloads with GitHub Actions

This repository is configured to automatically download FX rates every day using **GitHub Actions**. No external hosting or cron setup is required!

#### How it works

The workflow (`.github/workflows/download-fx-rates.yml`) runs daily at 06:30 UTC (12:00 PM IST):

1. Checks out the repository
2. Sets up Python with required dependencies (requests)
3. Runs `scripts/download_fx_rates.py` to fetch the latest rates
4. Automatically commits and pushes changes if any new rates are found

#### Manual Trigger

You can also trigger the workflow manually:

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Select **"Download FX Rates"** workflow
4. Click **Run workflow** → **Run workflow**

#### Customize the Schedule

To change the daily run time, edit [.github/workflows/download-fx-rates.yml](.github/workflows/download-fx-rates.yml):

```yaml
on:
  schedule:
    # Change the cron time (in UTC) as needed
    - cron: '30 6 * * *'  # Daily at 06:30 UTC / 12:00 PM IST
```

Common cron examples:
- `0 6 * * *` — Daily at 06:00 UTC
- `0 12 * * *` — Daily at 12:00 UTC (noon)
- `0 18 * * *` — Daily at 18:00 UTC
- `0 */6 * * *` — Every 6 hours

#### Run Locally

To test or run manually on your machine:

```bash
python scripts/download_fx_rates.py
python scripts/export_fx_rates_to_csv.py
```

The CSV output is saved to `banks/fx_rates.csv` and includes all banks in a single file with:
- `Bank`
The CSV output is saved to `banks/fx_rates.csv` with columns:
This file preserves historical rate records and appends new updates without removing previous entries.
| Column | Description |
|---|---|
| `Bank` | Bank name (HDFC, SBI, ICICI, IOB) |
| `Date` | Rate date (YYYY-MM-DD) |
| `Currency` | Full currency name |
| `Currency Code` | ISO 4217 code (USD, EUR, GBP …) |
| `TT Buy` | TT Buying rate vs INR |
| `TT Sell` | TT Selling rate vs INR |

This file preserves historical records and deduplicates on `(Bank, Date, Currency Code)`. New updates are appended; existing rows are never removed.

```bash
./scripts/update_repo.sh
```

#### Workflow Permissions

The workflow requires write access to the repository contents, which is configured via the **permissions** section in the workflow file. No additional setup needed!

#### Verify Output

After each successful run, the new files appear in:
- `banks/hdfc/` — HDFC PDFs
- `banks/sbi/` — SBI PDFs
- `banks/icici/` — ICICI PDFs/HTML
- `banks/iob/` — IOB PDFs/HTML
- `banks/fx_rates.csv` — Updated consolidated CSV

The Neon `fx_rates` table is also upserted with the latest records (no duplicates).

PDF files are named like `YYYY-MM-DD-<source-name>.pdf`.

#### Check Workflow Status

View the workflow runs and logs:
1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Click the **"Download FX Rates"** workflow
4. View run history and logs

#### Email Notifications (Optional)

To receive email notifications whenever FX rates are successfully updated, set up GitHub Secrets:
The notification email now includes a **per-bank summary table**:

```
Daily FX Rates Update
==========================================================
Time : 2026-04-29 06:32:01 UTC
Run  : https://github.com/<org>/<repo>/actions/runs/<id>

Neon DB — Bank-Level Summary:
----------------------------------------------------------
Bank      Dates    Rows  Latest        Earliest
----------------------------------------------------------
HDFC         11     292  2026-04-28    2026-04-13
ICICI        11     264  2026-04-28    2026-04-13
IOB          17     255  2026-04-28    2026-04-10
SBI          13     400  2026-04-28    2026-04-10
----------------------------------------------------------
Total rows in DB  : 1211
Rows upserted now : 35
CSV rows          : 1215
```

To enable email and Neon DB, set up GitHub Secrets:

**Option 1: Using Gmail**

1. [Create a Gmail App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled)
2. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
3. Add two secrets:
  - `EMAIL_USERNAME` — your Gmail address
  - `EMAIL_PASSWORD` — your Gmail app password
4. Email notifications will be sent on each successful update

**Option 2: Using another email provider**

You can modify the workflow file to use SMTP settings from your email provider (Outlook, Yahoo, etc.). Edit the `Send notification email` step in [.github/workflows/download-fx-rates.yml](.github/workflows/download-fx-rates.yml) with your provider's SMTP details.

#### Neon PostgreSQL Setup

1. Create a [Neon](https://neon.tech) project
2. Copy the connection string from the Neon dashboard
3. Add it as a repository secret:
   - `DATABASE_URL` — full Neon connection string (`postgresql://...?sslmode=require`)
4. The workflow will automatically create the table and indexes on first run

The `fx_rates` table schema:

```sql
CREATE TABLE fx_rates (
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
```

To backfill historical data manually:

```bash
DATABASE_URL="postgresql://..." python scripts/upload_to_neon.py
```

## Notes

- HDFC and SBI are downloaded directly as PDFs.
- ICICI and IOB are converted from HTML to PDF when possible; HTML snapshots are saved as fallback.
- SBI PDFs contain currency codes in `USD/INR` format — the parser extracts the foreign ISO code from the left side of the slash.
- **31 currencies** are supported for SBI: AED, AUD, BDT, BHD, CAD, CHF, CNY, DKK, EUR, GBP, HKD, IDR, JPY, KES, KRW, KWD, LKR, MYR, NOK, NZD, OMR, PKR, QAR, RUB, SAR, SEK, SGD, THB, TRY, USD, ZAR.
- The Neon upload step is gracefully skipped if `DATABASE_URL` is not configured.

## GitHub Pages Website

This repository now includes a static GitHub Pages site built from `index.html`, `styles.css`, and `app.js` in the repository root.

The published site is available at:

- `https://gupta-kanishk.github.io/india-fx-rates-archive/`

To publish it manually:

1. Go to the repository on GitHub.
2. Click **Settings** → **Pages**.
3. Under **Source**, choose **main** branch and **/ (root)**.
4. Save.

The site reads `banks/fx_rates.csv` and shows an interactive chart with bank, currency, and timeframe selectors.

## Troubleshooting

- **Workflow not running?** Check the **Actions** tab → workflow runs for error logs.
- **Missing dependencies?** The GitHub Actions workflow automatically installs Python and required packages (`pip install -r requirements.txt`).
- **Need to debug?** Run locally: `python scripts/download_fx_rates.py && python scripts/export_fx_rates_to_csv.py`
- **Files not committing?** Ensure the workflow has **write** permissions to repository contents (set in the workflow file).
- **Neon upload failing?** Verify `DATABASE_URL` secret is set and includes `?sslmode=require`.
- **SBI rates missing currencies?** Ensure the PDF URL is reachable — SBI occasionally moves the PDF path.
