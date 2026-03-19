# ==============================
# SIGNAL FILTER MODULE
# ==============================
# Removes weak signals, fake breakouts, and low-quality setups

class SignalFilter:
    """
    Filters out weak, unreliable signals
    Ensures only high-quality setups pass through
    """
    
    def __init__(self):
        self.filter_config = {
            'min_price': 0.50,              # Allow penny stocks (aggressive)
            'max_price': 100.00,            # Restrict to < $100 (capital efficiency)
            'min_volume_dollars': 50000,    # Min $50k daily volume (very relaxed)
            'min_rsi': 5,                   # RSI extreme lows allowed (very aggressive)
            'max_rsi': 95,                  # RSI extreme highs allowed (very aggressive)
            'min_ma_angle': -10,            # Any moving average trend ok (very permissive)
            'min_ml_confidence': 0.0,       # Accept ANY ML confidence (no filter)
            'min_sentiment_score': -1.0,   # Accept any sentiment (no filter)
        }
    
    def filter_signal(self, stock_data, signal):
        """
        Apply all filters to a signal
        Returns: (passes_filter: bool, reasons: list)
        """
        reasons = []
        passes = True
        
        # 1. Price filter - avoid penny stocks
        if stock_data['price'] < self.filter_config['min_price']:
            reasons.append(f"Price too low: ${stock_data['price']:.2f}")
            passes = False
        
        if stock_data['price'] > self.filter_config['max_price']:
            reasons.append(f"Price too high: ${stock_data['price']:.2f} (max: ${self.filter_config['max_price']})")
            passes = False
        
        # 2. Volume filter - ensure liquidity
        if 'volume_dollars' in stock_data:
            if stock_data['volume_dollars'] < self.filter_config['min_volume_dollars']:
                reasons.append(f"Volume too low: ${stock_data['volume_dollars']:,.0f}")
                passes = False
        
        # 3. RSI filter - avoid extremes
        rsi = signal['technical'].get('rsi', 50)
        if rsi < self.filter_config['min_rsi']:
            reasons.append(f"RSI too extreme low: {rsi:.1f}")
            passes = False
        if rsi > self.filter_config['max_rsi']:
            reasons.append(f"RSI too extreme high: {rsi:.1f}")
            passes = False
        
        # 4. MACD confirmation
        if signal['technical'].get('macd_trend') not in ['BULLISH', 'BEARISH']:
            reasons.append("MACD not confirmed")
            # Don't fail on this, but note it
        
        # 5. Moving average alignment
        ma_trend = signal['technical'].get('ma_trend')
        if ma_trend == 'SIDEWAYS':
            reasons.append("Price in consolidation (sideways)")
            # This is weak, could skip
        
        # 6. ML confidence
        ml_confidence = signal['ml_prediction'].get('confidence', 0)
        if ml_confidence < self.filter_config['min_ml_confidence']:
            reasons.append(f"ML confidence too low: {ml_confidence:.2f}")
            # Don't fail, but note it
        
        # 7. Volume expansion for breakouts
        if 'volume_ratio' in stock_data:
            if stock_data['volume_ratio'] < 0.8:
                reasons.append("Volume not expanded (weak breakout)")
        
        # 8. Sentiment confirmation
        sentiment_score = signal['sentiment'].get('overall_score', 0)
        if signal['signal'] == 'BUY' and sentiment_score < self.filter_config['min_sentiment_score']:
            reasons.append(f"Sentiment bearish: {sentiment_score:.2f}")
            # Don't block on sentiment alone
        
        return passes, reasons
    
    def filter_signals(self, results):
        """
        Filter multiple signals - AGGRESSIVE MODE: Pass all signals
        
        results: List of scanner results
        Returns: (filtered_results, filtered_out_reasons)
        """
        filtered = []
        filtered_out = {}
        
        for stock in results:
            ticker = stock['ticker']
            signal = stock.get('signal', 'HOLD')
            
            # AGGRESSIVE MODE: Pass everything!
            # In diamond hunting, we don't want to miss opportunities
            if signal in ['BUY', 'SELL']:
                filtered.append(stock)
            else:
                # Still include HOLD signals but separately log them
                filtered.append(stock)
        
        buy_signals = [s for s in filtered if s.get('signal') == 'BUY']
        sell_signals = [s for s in filtered if s.get('signal') == 'SELL']
        hold_signals = [s for s in filtered if s.get('signal') == 'HOLD']
        
        print(f"\n📊 SIGNAL FILTERING RESULTS:")
        print(f"  🟢 BUY signals: {len(buy_signals)}")
        print(f"  🔴 SELL signals: {len(sell_signals)}")
        print(f"  ⚪ HOLD signals: {len(hold_signals)}")
        
        return filtered, {}
    
    def get_filter_status(self):
        """
        Return current filter configuration
        """
        return {
            'min_price': f"${self.filter_config['min_price']:.2f}",
            'min_volume_dollars': f"${self.filter_config['min_volume_dollars']:,.0f}",
            'rsi_range': f"{self.filter_config['min_rsi']:.0f} - {self.filter_config['max_rsi']:.0f}",
            'min_ml_confidence': f"{self.filter_config['min_ml_confidence']:.2f}",
        }
