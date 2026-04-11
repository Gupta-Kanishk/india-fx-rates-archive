#!/usr/bin/env python3
"""
India FX Rates Archive - Python Version
Downloads and archives daily forex card/treasury FX rates from major Indian banks.
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from urllib.parse import urlparse


def ensure_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def download_file(url: str, destination: str, headers: Optional[Dict[str, str]] = None) -> bool:
    """Download a file from URL to destination."""
    try:
        # Remove existing file if it exists
        if os.path.exists(destination):
            os.remove(destination)

        response = requests.get(url, headers=headers, timeout=120, stream=True)
        response.raise_for_status()

        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify file was downloaded and has content
        if not os.path.exists(destination) or os.path.getsize(destination) == 0:
            if os.path.exists(destination):
                os.remove(destination)
            return False

        return True
    except Exception as e:
        print(f"  Download error: {e}")
        if os.path.exists(destination):
            os.remove(destination)
        return False


def fetch_html(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Fetch HTML content from URL."""
    try:
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  Fetch error: {e}")
        return None


def is_command_available(command: str) -> bool:
    """Check if a command is available on the system."""
    try:
        subprocess.run([command, '--version'],
                      capture_output=True,
                      check=True,
                      timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def convert_url_to_pdf_with_wkhtmltopdf(url: str, destination: str) -> bool:
    """Convert URL to PDF using wkhtmltopdf."""
    if not is_command_available('wkhtmltopdf'):
        return False

    try:
        # Remove existing file if it exists
        if os.path.exists(destination):
            os.remove(destination)

        # Use wkhtmltopdf to convert URL to PDF
        result = subprocess.run([
            'wkhtmltopdf',
            '--quiet',
            '--disable-smart-shrinking',
            '--print-media-type',
            '--page-size', 'A4',
            '--orientation', 'Portrait',
            url,
            destination
        ], capture_output=True, text=True, timeout=300)

        return result.returncode == 0 and os.path.exists(destination) and os.path.getsize(destination) > 0
    except Exception as e:
        print(f"  wkhtmltopdf error: {e}")
        if os.path.exists(destination):
            os.remove(destination)
        return False


def save_html_file(html: str, destination: str) -> bool:
    """Save HTML content to file."""
    try:
        # Remove existing file if it exists
        if os.path.exists(destination):
            os.remove(destination)

        with open(destination, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    except Exception as e:
        print(f"  Save HTML error: {e}")
        return False


def get_chrome_headers() -> Dict[str, str]:
    """Get Chrome browser headers to mimic real browser requests."""
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }


def download_bank_rates(source: Dict[str, Any], bank_dir: str, date: str) -> None:
    """Download rates for a specific bank."""
    source_type = source['type']
    filename = f"{date}-{source['filename']}"
    destination = os.path.join(bank_dir, filename)

    if source_type == 'pdf':
        print(f"Downloading {source['label']} PDF...")
        headers = get_chrome_headers() if 'icici' in source.get('bank', '').lower() else None

        if not download_file(source['url'], destination, headers):
            print(f"  Failed to download {source['label']} from {source['url']}")
            return

        print(f"  ✓ Saved {destination}")
        return

    if source_type == 'html':
        print(f"Fetching {source['label']} page...")

        # Use Chrome headers for ICICI specifically
        headers = get_chrome_headers() if 'icici' in source.get('bank', '').lower() else None
        html = fetch_html(source['url'], headers)

        if html is None:
            print(f"  ⚠ Failed to fetch HTML from {source['url']}")
            print("  Note: This may be a temporary issue or website blocking. Check the URL manually."
            return

        # Try wkhtmltopdf first
        if is_command_available('wkhtmltopdf'):
            print("  Converting HTML page to PDF with wkhtmltopdf...")
            if convert_url_to_pdf_with_wkhtmltopdf(source['url'], destination):
                print(f"  ✓ Saved {destination}")
                return

        # Fallback: save raw HTML
        html_filename = source.get('htmlFilename', source['filename'].replace('.pdf', '.html'))
        html_destination = os.path.join(bank_dir, f"{date}-{html_filename}")

        if save_html_file(html, html_destination):
            print(f"  wkhtmltopdf not available. Saved raw HTML to {html_destination}")
            return

        print(f"  Failed to save HTML file for {source['label']}")
        return

    print(f"Unknown source type '{source_type}' for {source['label']}")


def main() -> None:
    """Main function to download all bank rates."""
    # Set timezone to Asia/Kolkata
    os.environ['TZ'] = 'Asia/Kolkata'

    # Get script directory and set up paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    bank_root = base_dir / 'banks'

    # Get current date in YYYY-MM-DD format
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Bank sources configuration
    sources = [
        {
            'label': 'HDFC Bank Treasury Forex Card Rates',
            'type': 'pdf',
            'url': 'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf',
            'filename': 'hdfc-bank-treasury-forex-card-rates.pdf',
        },
        {
            'label': 'SBI Forex Card Rates',
            'type': 'pdf',
            'url': 'https://sbi.bank.in/documents/16012/1400784/FOREX_CARD_RATES.pdf',
            'filename': 'sbi-forex-card-rates.pdf',
        },
        {
            'label': 'ICICI Forex Card Rate',
            'type': 'html',
            'url': 'https://www.icici.bank.in/corporate/global-markets/forex/forex-card-rate',
            'filename': 'icici-forex-card-rates.pdf',
            'htmlFilename': 'icici-forex-card-rates.html',
            'bank': 'icici',
        },
        {
            'label': 'IOB Forex Rates',
            'type': 'html',
            'url': 'https://www.iob.bank.in/en/forex-rates',
            'filename': 'iob-forex-rates.pdf',
            'htmlFilename': 'iob-forex-rates.html',
            'bank': 'iob',
        },
    ]

    # Process each bank
    for source in sources:
        bank = source.get('bank', source['label'].split()[0].lower())
        bank_dir = bank_root / bank
        ensure_directory(str(bank_dir))
        download_bank_rates(source, str(bank_dir), current_date)

    print("Done.")


if __name__ == '__main__':
    main()