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
- ICICI: Website converted to PDF
- IOB: Website converted to PDF

## Features
- 📥 Automatic daily download using cPanel Cron
- 📄 Saves source PDFs directly when available
- 🌐 Converts HTML rate pages into PDF snapshots
- 🗂 Organizes files bank-wise and date-wise
- 🔁 Automatically pushes updates to GitHub
- 📚 Maintains historical FX rate archive