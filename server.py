import json
import mimetypes
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def sma(values, period):
    if len(values) < period:
        return None
    return mean(values[-period:])


def ema_series(values, period):
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)
    seed = mean(values[:period])
    series = [seed]

    for price in values[period:]:
        series.append((price - series[-1]) * multiplier + series[-1])
    return series


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []
    for index in range(1, period + 1):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = mean(gains)
    avg_loss = mean(losses)

    for index in range(period + 1, len(values)):
        delta = values[index] - values[index - 1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values):
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    if not ema12 or not ema26:
        return None

    offset = len(ema12) - len(ema26)
    macd_line = [ema12[index + offset] - ema26[index] for index in range(len(ema26))]
    signal_line = ema_series(macd_line, 9)
    if not signal_line:
        return None

    hist = macd_line[-1] - signal_line[-1]
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(hist, 4),
    }


def percent_change(current, reference):
    if reference in (0, None):
        return None
    return ((current - reference) / reference) * 100


def normalize_chart_result(raw):
    chart = raw.get("chart", {})
    results = chart.get("result") or []
    if not results:
        error = chart.get("error") or {}
        raise ValueError(error.get("description") or "No chart data returned.")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators") or {}).get("quote") or [{}]
    closes = quote[0].get("close") or []
    opens = quote[0].get("open") or []
    highs = quote[0].get("high") or []
    lows = quote[0].get("low") or []
    volumes = quote[0].get("volume") or []
    meta = result.get("meta") or {}

    points = []
    for index, timestamp in enumerate(timestamps):
        close = closes[index] if index < len(closes) else None
        if close is None:
            continue

        points.append(
            {
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                "open": opens[index] if index < len(opens) else None,
                "high": highs[index] if index < len(highs) else None,
                "low": lows[index] if index < len(lows) else None,
                "close": close,
                "volume": volumes[index] if index < len(volumes) else None,
            }
        )

    if not points:
        raise ValueError("No usable price points returned.")

    return {
        "symbol": meta.get("symbol"),
        "currency": meta.get("currency"),
        "exchangeName": meta.get("exchangeName"),
        "instrumentType": meta.get("instrumentType"),
        "regularMarketPrice": meta.get("regularMarketPrice"),
        "previousClose": meta.get("previousClose"),
        "chartPreviousClose": meta.get("chartPreviousClose"),
        "timezone": meta.get("exchangeTimezoneName"),
        "dataGranularity": meta.get("dataGranularity"),
        "range": meta.get("range"),
        "validRanges": meta.get("validRanges") or [],
        "points": points,
    }


def compute_analysis(chart_data, quote_data=None):
    closes = [point["close"] for point in chart_data["points"]]
    current = closes[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    rsi14 = rsi(closes, 14)
    macd_data = macd(closes)
    prev_close = chart_data.get("previousClose") or chart_data.get("chartPreviousClose")
    price_change_pct = percent_change(current, prev_close)

    score = 0
    reasons = []

    if sma20 and current > sma20:
        score += 1
        reasons.append("Price is above the 20-period average.")
    elif sma20:
        score -= 1
        reasons.append("Price is below the 20-period average.")

    if sma50 and current > sma50:
        score += 1
        reasons.append("Price is above the 50-period average.")
    elif sma50:
        score -= 1
        reasons.append("Price is below the 50-period average.")

    if sma20 and sma50 and sma20 > sma50:
        score += 1
        reasons.append("Short-term momentum is stronger than medium-term momentum.")
    elif sma20 and sma50:
        score -= 1
        reasons.append("Short-term momentum is weaker than medium-term momentum.")

    if rsi14 is not None:
        if rsi14 < 30:
            score += 1
            reasons.append("RSI is in oversold territory, which can support a bounce.")
        elif rsi14 > 70:
            score -= 1
            reasons.append("RSI is in overbought territory, which can signal exhaustion.")
        else:
            reasons.append("RSI is in a neutral range.")

    if macd_data:
        if macd_data["macd"] > macd_data["signal"]:
            score += 1
            reasons.append("MACD is above its signal line.")
        else:
            score -= 1
            reasons.append("MACD is below its signal line.")

    signal = "HOLD"
    if score >= 3:
        signal = "BUY"
    elif score <= -3:
        signal = "SELL"

    confidence = min(95, 50 + abs(score) * 9)

    trend = "Sideways"
    if sma20 and sma50 and current > sma20 > sma50:
        trend = "Bullish"
    elif sma20 and sma50 and current < sma20 < sma50:
        trend = "Bearish"

    analysis = {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "trend": trend,
        "currentPrice": round(current, 4),
        "previousClose": prev_close,
        "changePercentFromClose": round(price_change_pct, 2) if price_change_pct is not None else None,
        "indicators": {
            "sma20": round(sma20, 4) if sma20 else None,
            "sma50": round(sma50, 4) if sma50 else None,
            "sma200": round(sma200, 4) if sma200 else None,
            "rsi14": round(rsi14, 2) if rsi14 is not None else None,
            "macd": macd_data,
        },
        "reasons": reasons,
    }

    if quote_data:
        analysis["quote"] = quote_data

    return analysis


def fetch_quote(symbol: str):
    params = urlencode({"symbols": symbol})
    raw = fetch_json(f"{YAHOO_QUOTE_URL}?{params}")
    result = ((raw.get("quoteResponse") or {}).get("result") or [])
    if not result:
        return None

    quote = result[0]
    return {
        "symbol": quote.get("symbol"),
        "shortName": quote.get("shortName"),
        "longName": quote.get("longName"),
        "currency": quote.get("currency"),
        "marketState": quote.get("marketState"),
        "regularMarketPrice": quote.get("regularMarketPrice"),
        "regularMarketChange": quote.get("regularMarketChange"),
        "regularMarketChangePercent": quote.get("regularMarketChangePercent"),
        "regularMarketVolume": quote.get("regularMarketVolume"),
        "fiftyTwoWeekHigh": quote.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": quote.get("fiftyTwoWeekLow"),
        "averageDailyVolume3Month": quote.get("averageDailyVolume3Month"),
        "marketCap": quote.get("marketCap"),
    }


def fetch_chart(symbol: str, range_value: str, interval: str):
    params = urlencode({"range": range_value, "interval": interval, "includePrePost": "true"})
    url = YAHOO_CHART_URL.format(symbol=symbol) + f"?{params}"
    raw = fetch_json(url)
    return normalize_chart_result(raw)


class StockDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            return self.serve_file(STATIC_DIR / "index.html")
        if path.startswith("/static/"):
            relative_path = path.replace("/static/", "", 1)
            return self.serve_file(STATIC_DIR / relative_path)
        if path == "/api/stock":
            return self.handle_stock_api(parsed.query)

        self.send_error(404, "Not Found")

    def handle_stock_api(self, query_string):
        query = parse_qs(query_string)
        symbol = (query.get("symbol", ["AAPL"])[0] or "AAPL").upper()
        range_value = query.get("range", ["1d"])[0]
        interval = query.get("interval", ["5m"])[0]

        try:
            quote_data = fetch_quote(symbol)
            chart_data = fetch_chart(symbol, range_value, interval)
            analysis = compute_analysis(chart_data, quote_data)
            self.send_json(
                {
                    "ok": True,
                    "quote": quote_data,
                    "chart": chart_data,
                    "analysis": analysis,
                }
            )
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)
        except HTTPError as exc:
            self.send_json({"ok": False, "error": f"Upstream HTTP error: {exc.code}"}, status=502)
        except URLError:
            self.send_json(
                {
                    "ok": False,
                    "error": "Could not reach the market data provider. Check your connection and try again.",
                },
                status=502,
            )
        except Exception as exc:
            self.send_json({"ok": False, "error": f"Unexpected error: {exc}"}, status=500)

    def serve_file(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            return self.send_error(404, "File Not Found")

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"

        try:
            with open(file_path, "rb") as file:
                body = file.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            self.send_error(500, "Could not read file")

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def run():
    server = ThreadingHTTPServer((HOST, PORT), StockDashboardHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
