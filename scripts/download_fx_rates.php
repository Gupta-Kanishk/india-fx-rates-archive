<?php
declare(strict_types=1);

function ensureDirectory(string $path): void
{
    if (!is_dir($path) && !mkdir($path, 0755, true) && !is_dir($path)) {
        throw new RuntimeException("Unable to create directory: $path");
    }
}

function downloadFile(string $url, string $destination): bool
{
    // Remove existing file if it exists
    if (file_exists($destination)) {
        @unlink($destination);
    }

    $ch = curl_init($url);
    if ($ch === false) {
        return false;
    }

    $fp = fopen($destination, 'wb');
    if ($fp === false) {
        curl_close($ch);
        return false;
    }

    curl_setopt($ch, CURLOPT_FILE, $fp);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_FAILONERROR, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_TIMEOUT, 120);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);

    $success = curl_exec($ch);
    curl_close($ch);
    fclose($fp);

    if (!$success || !file_exists($destination) || filesize($destination) === 0) {
        @unlink($destination);
        return false;
    }

    return true;
}

function fetchHtml(string $url): ?string
{
    $ch = curl_init($url);
    if ($ch === false) {
        return null;
    }

    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_FAILONERROR, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_TIMEOUT, 120);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
    curl_setopt($ch, CURLOPT_ENCODING, 'gzip, deflate');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language: en-US,en;q=0.5',
        'Connection: keep-alive',
    ]);

    $html = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($html === false || $httpCode >= 400) {
        return null;
    }

    return $html;
}

function isCommandAvailable(string $command): bool
{
    if (!function_exists('shell_exec')) {
        return false;
    }

    $output = shell_exec(sprintf('command -v %s 2>/dev/null', escapeshellarg($command)));
    return trim((string)$output) !== '';
}

function convertUrlToPdfWithWkhtmltopdf(string $url, string $destination): bool
{
    if (!isCommandAvailable('wkhtmltopdf')) {
        return false;
    }

    // Remove existing file if it exists
    if (file_exists($destination)) {
        @unlink($destination);
    }

    $command = sprintf('wkhtmltopdf --quiet %s %s', escapeshellarg($url), escapeshellarg($destination));
    shell_exec($command);

    return file_exists($destination) && filesize($destination) > 0;
}

function convertHtmlToPdfWithDompdf(string $html, string $destination, string $basePath): bool
{
    if (!class_exists('Dompdf\Dompdf')) {
        return false;
    }

    // Remove existing file if it exists
    if (file_exists($destination)) {
        @unlink($destination);
    }

    $dompdf = new Dompdf\Dompdf();
    $dompdf->loadHtml($html);
    $dompdf->setPaper('A4', 'portrait');
    $dompdf->render();
    $pdfOutput = $dompdf->output();

    if ($pdfOutput === false) {
        return false;
    }

    return (bool)file_put_contents($destination, $pdfOutput);
}

function saveHtmlFile(string $html, string $destination): bool
{
    // Remove existing file if it exists
    if (file_exists($destination)) {
        @unlink($destination);
    }
    return file_put_contents($destination, $html) !== false;
}

function downloadBankRates(array $source, string $bankDir, string $date): void
{
    $type = $source['type'];
    $filename = $date . '-' . $source['filename'];
    $destination = $bankDir . DIRECTORY_SEPARATOR . $filename;

    if ($type === 'pdf') {
        echo "Downloading {$source['label']} PDF...\n";
        if (!downloadFile($source['url'], $destination)) {
            echo "  Failed to download {$source['label']} from {$source['url']}\n";
            return;
        }

        echo "  Saved {$destination}\n";
        return;
    }

    if ($type === 'html') {
        echo "Fetching {$source['label']} page...\n";
        $html = fetchHtml($source['url']);
        if ($html === null) {
            echo "  ⚠ Failed to fetch HTML from {$source['url']}\n";
            echo "  Note: This may be a temporary issue or website blocking. Check the URL manually.\n";
            return;
        }

        if (isCommandAvailable('wkhtmltopdf')) {
            echo "  Converting HTML page to PDF with wkhtmltopdf...\n";
            if (convertUrlToPdfWithWkhtmltopdf($source['url'], $destination)) {
                echo "  Saved {$destination}\n";
                return;
            }
        }

        if (class_exists('Dompdf\\Dompdf')) {
            echo "  Converting HTML page to PDF with Dompdf...\n";
            if (convertHtmlToPdfWithDompdf($html, $destination, $bankDir)) {
                echo "  Saved {$destination}\n";
                return;
            }
        }

        $htmlDestination = $bankDir . DIRECTORY_SEPARATOR . $date . '-' . $source['htmlFilename'];
        if (saveHtmlFile($html, $htmlDestination)) {
            echo "  wkhtmltopdf not available and Dompdf not installed. Saved raw HTML to {$htmlDestination}\n";
            return;
        }

        echo "  Failed to save HTML file for {$source['label']}\n";
        return;
    }

    echo "Unknown source type '{$type}' for {$source['label']}.\n";
}

function main(): void
{
    date_default_timezone_set('Asia/Kolkata');
    $baseDir = dirname(__DIR__);
    $bankRoot = $baseDir . '/banks';
    $date = date('Y-m-d');

    $sources = [
        [
            'label' => 'HDFC Bank Treasury Forex Card Rates',
            'type' => 'pdf',
            'url' => 'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf',
            'filename' => 'hdfc-bank-treasury-forex-card-rates.pdf',
        ],
        [
            'label' => 'SBI Forex Card Rates',
            'type' => 'pdf',
            'url' => 'https://sbi.bank.in/documents/16012/1400784/FOREX_CARD_RATES.pdf',
            'filename' => 'sbi-forex-card-rates.pdf',
        ],
        [
            'label' => 'ICICI Forex Card Rate',
            'type' => 'html',
            'url' => 'https://www.icici.bank.in/corporate/global-markets/forex/forex-card-rate',
            'filename' => 'icici-forex-card-rates.pdf',
            'htmlFilename' => 'icici-forex-card-rates.html',
            'bank' => 'icici',
        ],
        [
            'label' => 'IOB Forex Rates',
            'type' => 'html',
            'url' => 'https://www.iob.bank.in/en/forex-rates',
            'filename' => 'iob-forex-rates.pdf',
            'htmlFilename' => 'iob-forex-rates.html',
            'bank' => 'iob',
        ],
    ];

    foreach ($sources as $source) {
        $bank = $source['bank'] ?? strtolower(explode(' ', $source['label'])[0]);
        $bankDir = $bankRoot . '/' . $bank;
        ensureDirectory($bankDir);
        downloadBankRates($source, $bankDir, $date);
    }

    echo "Done.\n";
}

main();
