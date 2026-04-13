# SignalScope

SignalScope is a lightweight stock dashboard that fetches market data from Yahoo Finance, renders a browser-based chart, and generates simple rule-based trading signals.

## Features

- Quote lookup by stock symbol
- Price history chart for multiple time ranges and intervals
- Built-in indicator calculations:
  - SMA 20
  - SMA 50
  - SMA 200
  - RSI 14
  - MACD
- Simple BUY / HOLD / SELL signal generation
- No Python package installs required

## Run locally

```powershell
python server.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Notes

- Yahoo Finance data can be delayed depending on the symbol and market.
- The backend proxies data so the browser does not run into CORS issues.
- The signal engine is intentionally simple and should be treated as a screening tool, not financial advice.

## Next steps you can add

- Watchlists and local persistence
- WebSocket or polling refresh for auto-updating quotes
- Backtesting against historical bars
- News or fundamentals enrichment
- Alerting by email, Telegram, or Discord
