# ALPACA QUICK START GUIDE

Alpaca is now your default broker integration! ✓

**Alpaca vs WebULL:**
- ✅ Same penny stock support
- ✅ Easier API setup (no approval delays)
- ✅ Built-in paper trading ($100k virtual)
- ✅ Same commission-free trading
- ✅ Better Python documentation

---

## 🚀 SETUP ALPACA IN 5 MINUTES

### Step 1: Create Alpaca Account
1. Go to: https://app.alpaca.markets
2. Sign up with email
3. Verify email (instant)
4. Done! You now have a **paper trading account with $100,000 virtual funds**

### Step 2: Get API Credentials
1. Login to https://app.alpaca.markets
2. Click "Settings" (top right)
3. Click "API Keys"
4. Create new API key
5. Copy:
   - `API Key` (starts with letters)
   - `API Secret Key` (long string)

### Step 3: Add Credentials to .env
Edit your `.env` file (in project root) and replace:

```
ALPACA_API_KEY=paste_your_api_key_here
ALPACA_API_SECRET=paste_your_api_secret_here
```

**Example:**
```
ALPACA_API_KEY=PKxxxxxxxxxxxxx  
ALPACA_API_SECRET=w1xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 4: Test Connection
```bash
python -c "
from trading.alpaca_broker import AlpacaBroker
broker = AlpacaBroker()
print(f'Balance: ${broker.get_account_balance():.2f}')
"
```

Expected output:
```
[INFO] Alpaca Broker Integration
Mode: Paper Trading
Platform: Alpaca (Commission-free penny stock trading)
[OK] Connected to Alpaca
Balance: $100000.00
```

---

## 📋 WHAT CHANGED

**Files Updated:**
- ✅ `.env` - Now uses Alpaca credentials instead of WebULL
- ✅ `trading/alpaca_broker.py` - NEW Alpaca integration
- ✅ `trading/broker_integration.py` - Updated to use Alpaca
- ✅ `production_system.py` - Default broker set to 'alpaca'

**Files Deleted:**
- ❌ `trading/webull_broker.py` (replaced with Alpaca)
- ❌ WEBULL_SETUP.md, WEBULL_QUICKSTART.md (replaced with this file)

---

## 🔄 PAPER TRADING VS LIVE TRADING

### Paper Trading (DEFAULT - FREE)
- $100,000 virtual funds
- No real money needed
- Perfect for testing
- 100% same API as live

**Activate:**
```python
broker = AlpacaBroker(paper_trading=True)  # Default
```

### Live Trading (After Testing)
- Real money accounts
- Fund with actual $ (minimum $1)
- Same API, real orders
- Requires funded Alpaca account

**Switch when ready:**
```python
broker = AlpacaBroker(paper_trading=False)
```

---

## 🧪 TEST PAPER TRADING NOW

Run your automated session:
```bash
python automated_session.py  # Uses Alpaca paper trading
```

The system will:
1. ✓ Scan penny stocks (Alpha Vantage)
2. ✓ Generate BUY/SELL signals
3. ✓ Place orders to Alpaca (paper mode) 
4. ✓ Track positions & P/L

No real money risk - all virtual!

---

## 💰 WHEN READY FOR REAL TRADING

1. **Fund your Alpaca account:**
   - Dashboard → Transfers → Add Funds
   - Minimum: $1 (unlimited maximum)

2. **Switch to live mode:**
   - Edit `system_config.py` or
   - Set `paper_trading=False` in AlpacaBroker

3. **Start with small position sizes:**
   - Test with your $300
   - Verify orders execute
   - Monitor fills and commissions (should be $0)

---

## 🛠️ ALPACA BROKER API

Available methods:

```python
from trading.alpaca_broker import AlpacaBroker

broker = AlpacaBroker(paper_trading=True)

# Place orders
broker.place_buy_order('GME', shares=1, limit_price=25.00)
broker.place_sell_order('GME', shares=1, limit_price=30.00)

# Check positions 
positions = broker.get_positions()  # Dict of open positions

# Account info
balance = broker.get_account_balance()  # Buying power
print(f"Available: ${balance:.2f}")

# Order status
status = broker.get_order_status(order_id)
```

---

## ⚠️ IMPORTANT NOTES

1. **API Rate Limits:**
   - Paper trading: Unlimited
   - Live trading: Same unlimited
   - No rate limiting on Alpaca (unlike Alpha Vantage)

2. **Market Hours:**
   - Regular: 9:30 AM - 4:00 PM ET
   - Pre-market: 4:00 AM - 9:30 AM ET  
   - After-hours: 4:00 PM - 8:00 PM ET
   - Paper trading: Always open (24/7)

3. **Order Types:**
   - Market orders: Instant execution
   - Limit orders: Executes at price or better
   - Day orders: Cancelled at market close

4. **Penny Stocks:**
   - Alpaca supports all penny stocks
   - GME, AMC, BBBY fully supported
   - No restrictions like some brokers

---

## 📚 MORE RESOURCES

- **Alpaca Docs:** https://docs.alpaca.markets
- **Python SDK:** `pip install alpaca-trade-api`
- **API Status:** https://status.alpaca.markets

---

## ✅ SUMMARY

| Feature | Status |
|---------|--------|
| Data Source | Alpha Vantage ✓ |
| Broker | Alpaca ✓ |
| Paper Trading | Ready ✓ |
| Live Trading | Ready (after funding) |
| Scanner | Running ✓ |
| API Keys | Add to .env |

**Next steps:**
1. ✓ Add Alpaca API credentials to `.env`
2. ✓ Test connection
3. ✓ Run `python automated_session.py`
4. ✓ Paper trade for a few days
5. ✓ Fund account with real money
6. ✓ Switch to live trading

You're all set! 🚀
