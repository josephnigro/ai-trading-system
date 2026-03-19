# ==============================
# DASHBOARD MODULE (Visualization)
# ==============================

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime

class Dashboard:
    """
    Visual dashboard for scanner results
    """
    
    def __init__(self, results):
        self.results = results
        self.figsize = (16, 12)
    
    def create_overview_dashboard(self, filename='dashboard.png'):
        """
        Create comprehensive overview dashboard
        """
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        fig.suptitle('AI Trading Scanner Dashboard', fontsize=20, fontweight='bold')
        
        # 1. Signal Distribution
        self.plot_signal_distribution(axes[0, 0])
        
        # 2. Price Distribution
        self.plot_price_distribution(axes[0, 1])
        
        # 3. Technical Score Distribution
        self.plot_technical_scores(axes[1, 0])
        
        # 4. Sentiment Distribution
        self.plot_sentiment_distribution(axes[1, 1])
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✓ Dashboard saved to {filename}")
        return fig
    
    def plot_signal_distribution(self, ax):
        """
        Plot BUY/SELL/HOLD signal distribution
        """
        signals = pd.Series([r['signal'] for r in self.results])
        counts = signals.value_counts()
        
        colors = {'BUY': '#2ecc71', 'SELL': '#e74c3c', 'HOLD': '#f39c12'}
        colors_list = [colors.get(signal, '#95a5a6') for signal in counts.index]
        
        ax.bar(counts.index, counts.values, color=colors_list, edgecolor='black', linewidth=2)
        ax.set_title('Trading Signals Distribution', fontweight='bold', fontsize=14)
        ax.set_ylabel('Count', fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        for i, v in enumerate(counts.values):
            ax.text(i, v + 0.1, str(v), ha='center', fontweight='bold')
    
    def plot_price_distribution(self, ax):
        """
        Plot price distribution of analyzed stocks
        """
        prices = [r['price'] for r in self.results]
        
        ax.hist(prices, bins=15, color='#3498db', edgecolor='black', alpha=0.7)
        ax.set_title('Stock Price Distribution', fontweight='bold', fontsize=14)
        ax.set_xlabel('Price ($)', fontweight='bold')
        ax.set_ylabel('Frequency', fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        ax.axvline(np.mean(prices), color='red', linestyle='--', linewidth=2, label=f'Mean: ${np.mean(prices):.2f}')
        ax.legend()
    
    def plot_technical_scores(self, ax):
        """
        Plot technical analysis scores
        """
        scores = [r['technical']['score'] for r in self.results]
        tickers = [r['ticker'] for r in self.results]
        
        # Sort and take top/bottom
        sorted_indices = np.argsort(scores)
        top_n = 10
        
        top_indices = sorted_indices[-top_n:]
        bottom_indices = sorted_indices[:top_n]
        
        combined_indices = list(bottom_indices) + list(top_indices)
        combined_tickers = [tickers[i] for i in combined_indices]
        combined_scores = [scores[i] for i in combined_indices]
        
        colors = ['#e74c3c' if s < 0 else '#2ecc71' for s in combined_scores]
        
        ax.barh(combined_tickers, combined_scores, color=colors, edgecolor='black')
        ax.set_title('Technical Analysis Scores (Top/Bottom)', fontweight='bold', fontsize=14)
        ax.set_xlabel('Score', fontweight='bold')
        ax.axvline(0, color='black', linestyle='-', linewidth=1)
        ax.grid(axis='x', alpha=0.3)
    
    def plot_sentiment_distribution(self, ax):
        """
        Plot sentiment distribution
        """
        sentiments = [r['sentiment']['overall_sentiment'] for r in self.results]
        sentiment_scores = [r['sentiment']['overall_score'] for r in self.results]
        
        sentiment_mapping = {
            'VERY_BULLISH': 2,
            'BULLISH': 1,
            'NEUTRAL': 0,
            'BEARISH': -1,
            'VERY_BEARISH': -2
        }
        
        sentiment_values = [sentiment_mapping.get(s, 0) for s in sentiments]
        
        colors = ['#27ae60' if v > 1 else '#2ecc71' if v > 0 else '#95a5a6' if v == 0 else '#e74c3c' if v > -1 else '#c0392b' for v in sentiment_values]
        
        ax.scatter(range(len(sentiment_scores)), sentiment_scores, c=colors, s=100, alpha=0.6, edgecolor='black')
        ax.set_title('Sentiment Analysis Scores', fontweight='bold', fontsize=14)
        ax.set_ylabel('Sentiment Score', fontweight='bold')
        ax.set_xlabel('Stock Index', fontweight='bold')
        ax.axhline(0, color='black', linestyle='--', linewidth=1)
        ax.grid(alpha=0.3)
    
    def create_top_signals_report(self, top_n=10, filename='top_signals.png'):
        """
        Create detailed report of top BUY signals
        """
        buy_stocks = [r for r in self.results if r['signal'] == 'BUY']
        
        if not buy_stocks:
            print("No BUY signals to report")
            return
        
        # Sort by technical score
        buy_stocks = sorted(buy_stocks, key=lambda x: x['technical']['score'], reverse=True)[:top_n]
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        tickers = [s['ticker'] for s in buy_stocks]
        prices = [s['price'] for s in buy_stocks]
        tech_scores = [s['technical']['score'] for s in buy_stocks]
        ml_confidence = [s['ml_prediction']['confidence'] for s in buy_stocks]
        
        x = np.arange(len(tickers))
        width = 0.25
        
        ax.bar(x - width, tech_scores, width, label='Technical Score', color='#3498db')
        ax.bar(x, ml_confidence, width, label='ML Confidence', color='#2ecc71')
        
        ax.set_title(f'Top {top_n} BUY Signals - Detailed Analysis', fontweight='bold', fontsize=16)
        ax.set_ylabel('Score / Confidence', fontweight='bold')
        ax.set_xlabel('Stock Ticker', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(tickers, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✓ Top signals report saved to {filename}")
        return fig
    
    def show(self):
        """
        Display all plots
        """
        self.create_overview_dashboard()
        self.create_top_signals_report()
        print("\nDashboards created successfully!")
