# AI Trading Scanner - Quick Start Guide

## What You Have

A complete **AI-powered stock trading scanner** with:

### Modules:
1. **data_engine.py** - Fetches real stock data from Yahoo Finance
2. **technical_analysis.py** - RSI, MACD, Moving Average analysis
3. **ml_predictor.py** - Machine Learning price prediction models
4. **sentiment_analyzer.py** - Market sentiment analysis
5. **Scanner.py** - Main orchestrator (runs everything)
6. **dashboard.py** - Visual dashboards and charts

## How to Use

### Method 1: Run from Terminal
```powershell
cd c:\Users\joe\Documents\AI_Stock_Trading\Scanner\AI_Trading_Scanner
.venv\Scripts\python.exe Scanner.py
```

### Method 2: Run a Custom Scan
Create a file `my_scan.py`:
```python
from Scanner import AITradingScanner

# Scan specific stocks
scanner = AITradingScanner(['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'])
results = scanner.scan(period="3mo")
scanner.print_results(top_n=10)
scanner.export_to_csv('my_results.csv')
```

Then run:
```powershell
.venv\Scripts\python.exe my_scan.py
```

### Method 3: Generate Visualizations
```python
from Scanner import AITradingScanner
from dashboard import Dashboard

scanner = AITradingScanner()
results = scanner.scan(period="3mo")
dashboard = Dashboard(results)
dashboard.show()
```

## Trading Signals Explained

### BUY Signal
- Technical analysis is positive (RSI < 30, MACD bullish, price above moving averages)
- ML model predicts upward movement
- Market sentiment is bullish
- **Action**: Consider buying

### SELL Signal
- Technical analysis is negative (RSI > 70, MACD bearish, price below moving averages)
- ML model predicts downward movement
- Market sentiment is bearish
- **Action**: Consider selling or taking profits

### HOLD Signal
- Mixed signals or neutral indicators
- Keep monitoring

## Key Indicators Used

| Indicator | What It Means |
|-----------|---------------|
| **RSI** | If < 30: Oversold (BUY). If > 70: Overbought (SELL) |
| **MACD** | Bullish if above signal line, Bearish if below |
| **Moving Averages** | Price above MA = Uptrend, Price below MA = Downtrend |
| **ML Prediction** | Uses recent price action to predict next day direction |
| **Sentiment** | Overall market feeling based on momentum & volume |

## Output Files

After running a scan:
- `scanner_results.csv` - Detailed results for all stocks
- `dashboard.png` - Overview visualization
- `top_signals.png` - Detailed top BUY signals

## Configuration

By default, scans:
- **Stocks**: Top 25 S&P 500 companies (can customize)
- **Period**: 1 year of historical data (better for ML training)
- **Update**: Daily (end of day)

To modify, edit the `SP500_TICKERS` list in Scanner.py

## Next Steps

1. Run your first scan: `.venv\Scripts\python.exe Scanner.py`
2. Check `scanner_results.csv` for results
3. Modify tickers as needed
4. Generate visualizations with dashboard.py
5. Schedule daily runs (use Windows Task Scheduler)

## Performance Note

- First scan takes 30-60 seconds (downloads data for all stocks)
- Subsequent scans are faster due to caching
- Each stock analysis takes ~1-2 seconds

---

**Your AI Trading Scanner is ready to use!**
