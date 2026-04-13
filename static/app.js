const controls = document.getElementById("controls");
const symbolInput = document.getElementById("symbolInput");
const rangeInput = document.getElementById("rangeInput");
const intervalInput = document.getElementById("intervalInput");
const companyName = document.getElementById("companyName");
const marketState = document.getElementById("marketState");
const priceValue = document.getElementById("priceValue");
const changeValue = document.getElementById("changeValue");
const metaStats = document.getElementById("metaStats");
const signalValue = document.getElementById("signalValue");
const trendValue = document.getElementById("trendValue");
const signalSummary = document.getElementById("signalSummary");
const reasonsList = document.getElementById("reasonsList");
const confidenceBadge = document.getElementById("confidenceBadge");
const indicatorGrid = document.getElementById("indicatorGrid");
const chartMeta = document.getElementById("chartMeta");
const chart = document.getElementById("chart");

function formatNumber(value, options = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return new Intl.NumberFormat("en-US", options).format(value);
}

function formatCurrency(value, currency = "USD") {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: value >= 100 ? 2 : 4,
  }).format(value);
}

function formatCompact(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function setTone(element, tone) {
  element.classList.remove("positive", "negative", "neutral");
  element.classList.add(tone);
}

function updateQuote(data) {
  const quote = data.quote || {};
  const chartData = data.chart || {};
  const currency = quote.currency || chartData.currency || "USD";
  const changePercent = quote.regularMarketChangePercent ?? data.analysis.changePercentFromClose;
  const tone = changePercent > 0 ? "positive" : changePercent < 0 ? "negative" : "neutral";

  companyName.textContent = quote.longName || quote.shortName || chartData.symbol || "Unknown symbol";
  marketState.textContent = quote.marketState || "Unknown";
  priceValue.textContent = formatCurrency(data.analysis.currentPrice, currency);
  changeValue.textContent = changePercent === null || changePercent === undefined
    ? "--"
    : `${changePercent >= 0 ? "+" : ""}${changePercent.toFixed(2)}%`;
  setTone(changeValue, tone);
  setTone(marketState, tone === "neutral" ? "neutral" : tone);

  metaStats.innerHTML = "";
  const stats = [
    ["Volume", formatCompact(quote.regularMarketVolume)],
    ["Avg Vol", formatCompact(quote.averageDailyVolume3Month)],
    ["52W High", formatCurrency(quote.fiftyTwoWeekHigh, currency)],
    ["52W Low", formatCurrency(quote.fiftyTwoWeekLow, currency)],
    ["Market Cap", formatCompact(quote.marketCap)],
  ];

  stats.forEach(([label, value]) => {
    const stat = document.createElement("div");
    stat.className = "meta-stat";
    stat.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    metaStats.appendChild(stat);
  });
}

function updateAnalysis(data) {
  const analysis = data.analysis;
  const tone = analysis.signal === "BUY" ? "positive" : analysis.signal === "SELL" ? "negative" : "neutral";

  signalValue.textContent = analysis.signal;
  trendValue.textContent = `Trend: ${analysis.trend}`;
  signalSummary.textContent = `Score ${analysis.score} with ${analysis.confidence}% confidence based on moving averages, RSI, and MACD.`;
  confidenceBadge.textContent = `${analysis.confidence}%`;

  setTone(signalValue, tone);
  setTone(confidenceBadge, tone);

  reasonsList.innerHTML = "";
  analysis.reasons.forEach((reason) => {
    const item = document.createElement("li");
    item.textContent = reason;
    reasonsList.appendChild(item);
  });

  indicatorGrid.innerHTML = "";
  const indicators = [
    ["SMA 20", analysis.indicators.sma20],
    ["SMA 50", analysis.indicators.sma50],
    ["SMA 200", analysis.indicators.sma200],
    ["RSI 14", analysis.indicators.rsi14],
    ["MACD", analysis.indicators.macd ? analysis.indicators.macd.macd : null],
    ["MACD Signal", analysis.indicators.macd ? analysis.indicators.macd.signal : null],
  ];

  indicators.forEach(([label, value]) => {
    const tile = document.createElement("div");
    tile.className = "indicator";
    tile.innerHTML = `<span>${label}</span><strong>${value === null || value === undefined ? "--" : formatNumber(value, { maximumFractionDigits: 2 })}</strong>`;
    indicatorGrid.appendChild(tile);
  });
}

function updateChart(data) {
  const points = data.chart.points || [];
  if (!points.length) {
    chart.innerHTML = "";
    chartMeta.textContent = "No chart data";
    return;
  }

  const values = points.map((point) => point.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 900;
  const height = 320;
  const padding = 18;

  const linePath = points.map((point, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((point.close - min) / range) * (height - padding * 2);
    return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");

  const areaPath = `${linePath} L ${width - padding} ${height - padding} L ${padding} ${height - padding} Z`;
  const tone = values[values.length - 1] >= values[0] ? "positive" : "negative";

  chart.innerHTML = `
    <defs>
      <linearGradient id="fillGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${tone === "positive" ? "#23c27d" : "#f45b69"}" stop-opacity="0.45"></stop>
        <stop offset="100%" stop-color="${tone === "positive" ? "#23c27d" : "#f45b69"}" stop-opacity="0.04"></stop>
      </linearGradient>
    </defs>
    <path d="${areaPath}" fill="url(#fillGradient)"></path>
    <path d="${linePath}" class="chart-line ${tone}"></path>
  `;

  const latest = points[points.length - 1];
  const started = new Date(points[0].timestamp * 1000);
  const ended = new Date(latest.timestamp * 1000);
  chartMeta.textContent = `${data.chart.range} • ${data.chart.dataGranularity} • ${started.toLocaleDateString()} to ${ended.toLocaleDateString()}`;
}

function showLoading() {
  companyName.textContent = "Fetching market data...";
  signalSummary.textContent = "Updating price, chart, and analysis.";
}

function showError(message) {
  companyName.textContent = "Request failed";
  signalSummary.textContent = message;
  chart.innerHTML = "";
}

async function fetchStock(event) {
  if (event) {
    event.preventDefault();
  }

  const symbol = symbolInput.value.trim().toUpperCase() || "AAPL";
  const range = rangeInput.value;
  const interval = intervalInput.value;

  showLoading();

  const response = await fetch(`/api/stock?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`);
  const payload = await response.json();

  if (!payload.ok) {
    showError(payload.error || "Unknown error");
    return;
  }

  updateQuote(payload);
  updateAnalysis(payload);
  updateChart(payload);
}

controls.addEventListener("submit", (event) => {
  fetchStock(event).catch((error) => showError(error.message));
});

fetchStock().catch((error) => showError(error.message));
