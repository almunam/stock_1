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

## Deploy on Render

1. Push the repository to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Select this repository: `almunam/stock_1`.
4. Render will detect `render.yaml` and create the web service.
5. Deploy the service and open the generated Render URL.

The app uses the `PORT` environment variable provided by Render and binds to `0.0.0.0` in production.

## Alternative deploy option

- Railway can also run this project.
- Set the start command to `python server.py`.
- Railway will inject `PORT` automatically, and the app will use it.

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
