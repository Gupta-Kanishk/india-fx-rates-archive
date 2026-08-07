const bankSelect = document.getElementById('bankSelect');
const currencySelect = document.getElementById('currencySelect');
const timeframeSelect = document.getElementById('timeframeSelect');
const chartSubtitle = document.getElementById('chartSubtitle');
const statsPanel = document.getElementById('statsPanel');
const errorMessage = document.getElementById('errorMessage');
const chartCanvas = document.getElementById('fxChart');

let fxChart = null;
let archive = {};
let availableBanks = [];
let selectedBank;
let selectedCurrency;
let selectedTimeframe;

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines.shift();
  if (!header) return [];

  return lines
    .map(line => line.split(','))
    .map(cols => ({
      bank: cols[0] || '',
      date: cols[1] || '',
      currency: cols[2] || '',
      currencyCode: cols[3] || '',
      ttBuy: parseFloat(cols[4]) || null,
      ttSell: parseFloat(cols[5]) || null,
    }))
    .filter(row => row.bank && row.date && row.currencyCode);
}

function groupRates(rows) {
  const grouped = {};
  rows.forEach(row => {
    const key = `${row.bank}||${row.currencyCode}`;
    if (!grouped[key]) {
      grouped[key] = {
        bank: row.bank,
        currency: row.currency,
        currencyCode: row.currencyCode,
        records: [],
      };
    }
    grouped[key].records.push(row);
  });

  Object.values(grouped).forEach(item => {
    item.records.sort((a, b) => a.date.localeCompare(b.date));
  });

  return grouped;
}

function buildArchive(rows) {
  const grouped = groupRates(rows);
  const banks = [...new Set(rows.map(r => r.bank))].sort();
  const archiveByBank = {};

  banks.forEach(bank => {
    archiveByBank[bank] = [];
  });

  Object.values(grouped).forEach(item => {
    archiveByBank[item.bank].push(item);
  });

  Object.keys(archiveByBank).forEach(bank => {
    archiveByBank[bank].sort((a, b) => a.currencyCode.localeCompare(b.currencyCode));
  });

  return { archiveByBank, banks };
}

function createOption(value, label) {
  const option = document.createElement('option');
  option.value = value;
  option.textContent = label;
  return option;
}

function populateBankSelect() {
  bankSelect.innerHTML = '';
  availableBanks.forEach(bank => {
    bankSelect.appendChild(createOption(bank, bank));
  });
}

function populateCurrencySelect(bank) {
  currencySelect.innerHTML = '';
  const currencies = archive[bank] || [];
  currencies.forEach(item => {
    currencySelect.appendChild(createOption(item.currencyCode, `${item.currency} (${item.currencyCode})`));
  });
}

function pickDefaultSelections() {
  selectedBank = bankSelect.value || availableBanks[0];
  selectedCurrency = currencySelect.value || (archive[selectedBank]?.[0]?.currencyCode ?? '');
  selectedTimeframe = timeframeSelect.value;
}

function applyTimeframe(records, timeframe) {
  if (timeframe === 'all') return records;
  const limit = parseInt(timeframe, 10);
  return records.slice(-limit);
}

function formatCurrencyDate(dateString) {
  const date = new Date(dateString + 'T00:00:00Z');
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
}

function createChartData(records) {
  const labels = records.map(r => formatCurrencyDate(r.date));
  const buyData = records.map(r => r.ttBuy);
  const sellData = records.map(r => r.ttSell);
  return { labels, buyData, sellData };
}

function renderStats(recordSet) {
  if (!recordSet.length) {
    statsPanel.innerHTML = '<p>No history available for this selection.</p>';
    return;
  }

  const latest = recordSet[recordSet.length - 1];
  const first = recordSet[0];
  statsPanel.innerHTML = `
    <p><strong>Bank</strong><br />${selectedBank}</p>
    <p><strong>Currency</strong><br />${selectedCurrency}</p>
    <p><strong>Dates</strong><br />${formatCurrencyDate(first.date)} → ${formatCurrencyDate(latest.date)}</p>
    <p><strong>Latest TT Buy</strong><br />${latest.ttBuy ?? 'N/A'}</p>
    <p><strong>Latest TT Sell</strong><br />${latest.ttSell ?? 'N/A'}</p>
  `;
}

function showError(message) {
  errorMessage.hidden = false;
  errorMessage.textContent = message;
}

function clearError() {
  errorMessage.hidden = true;
  errorMessage.textContent = '';
}

function renderChart() {
  const series = archive[selectedBank]?.find(item => item.currencyCode === selectedCurrency);
  if (!series) {
    showError('Selected bank or currency has no data.');
    return;
  }

  clearError();
  const filteredRecords = applyTimeframe(series.records, selectedTimeframe);
  const validRecords = filteredRecords.filter(record => record.ttBuy !== null || record.ttSell !== null);

  if (!validRecords.length) {
    showError('No numeric TT Buy or TT Sell values are available for the selected timeframe.');
    chartSubtitle.textContent = 'No chart data available.';
    if (fxChart) {
      fxChart.data.labels = [];
      fxChart.data.datasets.forEach(set => (set.data = []));
      fxChart.update();
    }
    renderStats([]);
    return;
  }

  const { labels, buyData, sellData } = createChartData(validRecords);
  chartSubtitle.textContent = `Showing ${validRecords.length} records for ${selectedCurrency} from ${formatCurrencyDate(validRecords[0].date)} to ${formatCurrencyDate(validRecords[validRecords.length - 1].date)}.`;
  renderStats(validRecords);

  const datasets = [
    {
      label: 'TT Buy',
      data: buyData,
      borderColor: '#2563eb',
      backgroundColor: 'rgba(37, 99, 235, 0.15)',
      tension: 0.25,
      spanGaps: true,
    },
    {
      label: 'TT Sell',
      data: sellData,
      borderColor: '#ea580c',
      backgroundColor: 'rgba(249, 115, 22, 0.14)',
      tension: 0.25,
      spanGaps: true,
    },
  ];

  if (!fxChart) {
    fxChart = new Chart(chartCanvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
          },
          tooltip: {
            callbacks: {
              label: context => {
                const value = context.parsed.y;
                return `${context.dataset.label}: ${value != null ? value.toFixed(4) : 'N/A'}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
            ticks: {
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 12,
            },
          },
          y: {
            title: {
              display: true,
              text: 'INR per unit',
            },
            grid: {
              color: 'rgba(15, 23, 42, 0.08)',
            },
          },
        },
      },
    });
  } else {
    fxChart.data.labels = labels;
    fxChart.data.datasets = datasets;
    fxChart.update();
  }
}

function onSelectionChange() {
  selectedBank = bankSelect.value;
  selectedCurrency = currencySelect.value;
  selectedTimeframe = timeframeSelect.value;
  renderChart();
}

function setupEventListeners() {
  bankSelect.addEventListener('change', () => {
    selectedBank = bankSelect.value;
    populateCurrencySelect(selectedBank);
    selectedCurrency = currencySelect.value;
    renderChart();
  });

  currencySelect.addEventListener('change', () => onSelectionChange());
  timeframeSelect.addEventListener('change', () => onSelectionChange());
}

function loadCsv() {
  const localFile = './banks/fx_rates.csv';
  return fetch(localFile).then(response => {
    if (!response.ok) {
      throw new Error('Failed to load local CSV');
    }
    return response.text();
  }).catch(() => {
    const fallback = 'https://raw.githubusercontent.com/Gupta-Kanishk/india-fx-rates-archive/main/banks/fx_rates.csv';
    return fetch(fallback).then(response => {
      if (!response.ok) {
        throw new Error('Failed to load CSV from fallback URL');
      }
      return response.text();
    });
  });
}

function initialize() {
  loadCsv()
    .then(text => {
      const rows = parseCsv(text);
      const built = buildArchive(rows);
      archive = built.archiveByBank;
      availableBanks = built.banks;

      if (!availableBanks.length) {
        throw new Error('No FX rate data found in the CSV file.');
      }

      populateBankSelect();
      populateCurrencySelect(availableBanks[0]);
      pickDefaultSelections();
      setupEventListeners();
      renderChart();
    })
    .catch(error => {
      errorMessage.hidden = false;
      errorMessage.textContent = `Unable to load FX rates: ${error.message}`;
      chartSubtitle.textContent = 'Please check that the repository and CSV file are accessible.';
    });
}

initialize();
