# 🇮🇳 India FX Rates Archive

A public automated repository that **downloads and archives daily forex card / treasury FX rates** from major Indian banks.

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

## Repository Layout
- `banks/hdfc/` — HDFC PDF archive
- `banks/sbi/` — SBI PDF archive
- `banks/icici/` — ICICI HTML + PDF archive
- `banks/iob/` — IOB HTML + PDF archive
- `scripts/download_fx_rates.py` — Downloads source files and converts HTML pages to PDF
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
- `Date`
- `Currency`
- `Currency Code`
- `TT Buy`
- `TT Sell`

This file preserves historical rate records and appends new updates without removing previous entries.

With git commit and push:

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

PDF files are named like `YYYY-MM-DD-<source-name>.pdf`.

#### Check Workflow Status

View the workflow runs and logs:
1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Click the **"Download FX Rates"** workflow
4. View run history and logs

#### Email Notifications (Optional)

To receive email notifications whenever FX rates are successfully updated, set up GitHub Secrets:

**Option 1: Using Gmail**

1. [Create a Gmail App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled)
2. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
3. Add two secrets:
   - `EMAIL_USERNAME` — your Gmail address (e.g., `your-email@gmail.com`)
   - `EMAIL_PASSWORD` — your Gmail app password
4. Email notifications will be sent to `analyst.kanishk@gmail.com` on each successful update

**Option 2: Using another email provider**

You can modify the workflow file to use SMTP settings from your email provider (Outlook, Yahoo, etc.). Edit the `Send notification email` step in [.github/workflows/download-fx-rates.yml](.github/workflows/download-fx-rates.yml) with your provider's SMTP details.

## Notes

- HDFC and SBI are downloaded directly as PDFs.
- ICICI and IOB are converted from HTML to PDF when possible.
- If conversion is unavailable, HTML snapshots are still saved under the same bank folder.

## Troubleshooting

- **Workflow not running?** Check the **Actions** tab → workflow runs for error logs.
- **Missing dependencies?** The GitHub Actions workflow automatically installs Python and required packages.
- **Need to debug?** Run `python scripts/download_fx_rates.py` locally to test the script directly.
- **Files not committing?** Ensure the workflow has **write** permissions to repository contents (checked automatically).
