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
- 📥 Automatic daily download using cPanel Cron
- 📄 Saves source PDFs directly when available
- 🌐 Converts HTML rate pages into PDF snapshots
- 🗂 Organizes files bank-wise and date-wise
- 🔁 Automatically pushes updates to GitHub
- 📚 Maintains historical FX rate archive

## Repository Layout
- `banks/hdfc/` — HDFC PDF archive
- `banks/sbi/` — SBI PDF archive
- `banks/icici/` — ICICI HTML + PDF archive
- `banks/iob/` — IOB HTML + PDF archive
- `scripts/download_fx_rates.php` — Downloads source files and converts HTML pages to PDF
- `scripts/update_repo.sh` — Runs download, commits changes, and pushes to GitHub

## Setup

### 1. Clone this repo to cPanel

Use SSH if possible:

```bash
cd ~/public_html
git clone git@github.com:<your-user>/<your-repo>.git
cd <your-repo>
chmod +x scripts/update_repo.sh
```

If you cannot use SSH, set up a GitHub personal access token and use HTTPS.

### 2. Install conversion tools (optional)

For HTML pages, the script tries to convert using `wkhtmltopdf` first.
If `wkhtmltopdf` is not installed, the script saves the raw HTML page as a fallback.

On cPanel, ask your host to enable `wkhtmltopdf` or install it in your account.

### 3. Run manually once

```bash
cd ~/public_html/<your-repo>
php scripts/download_fx_rates.php
```

### 4. Set up a cPanel Cron job

Use cPanel Cron Jobs to run the update script every day.

Example command:

```bash
cd /home/<username>/public_html/<your-repo> && ./scripts/update_repo.sh >> /home/<username>/fx-rates.log 2>&1
```

Example schedule:
- `0 06 * * *` — run every day at 06:00 server time

### 5. Configure GitHub Push

If using SSH, ensure your cPanel user has an SSH key added to GitHub.

If using HTTPS, set your remote URL with a personal access token (not recommended for security reasons):

```bash
git remote set-url origin https://<github-username>:<token>@github.com/<github-username>/<repo>.git
```

### 6. Verify output

After a successful run, the new files will be saved in:
- `banks/hdfc/`
- `banks/sbi/`
- `banks/icici/`
- `banks/iob/`

PDF files are named like `YYYY-MM-DD-<source-name>.pdf`.

## Notes

- HDFC and SBI are downloaded directly as PDFs.
- ICICI and IOB are converted from HTML to PDF when possible.
- If conversion is unavailable, HTML snapshots are still saved under the same bank folder.

## Troubleshooting

- If `php scripts/download_fx_rates.php` fails, verify that `curl` is enabled in PHP.
- If the cron job does not push, confirm `git` is available in your cPanel account and `origin` is configured correctly.
