import numpy as np
import pandas as pd
from portfolio_engine import BaseAllocator
from portfolio_pipeline import engine
from pipeline_core import load_price_series

class InverseVolatilityAllocator(BaseAllocator):
    """Allocator that assigns weights inversely proportional to 20-day historical volatility.
    
    Volatility is calculated as the standard deviation of daily percentage returns
    over the 20 trading days up to and including the given date.
    """
    
    def __init__(self, prices=None):
        if prices is None:
            self.prices = load_price_series()
        else:
            self.prices = prices
        # Precompute daily returns
        self.returns = {}
        for ticker, series in self.prices.items():
            self.returns[ticker] = series.pct_change()
            
    def allocate(self, ranked_stocks, date=None, portfolio_state=None):
        if ranked_stocks is None or ranked_stocks.empty or date is None:
            return {}
            
        weights = {}
        target_date = pd.Timestamp(date)
        
        for _, row in ranked_stocks.iterrows():
            ticker = row['Ticker']
            if ticker not in self.returns:
                continue
                
            ret_series = self.returns[ticker]
            # Use loc to get all returns up to the date, then take last 20
            window = ret_series.loc[:target_date].iloc[-20:]
            
            # Need at least 20 returns
            if len(window) < 20:
                continue
            
            # Calculate volatility (standard deviation of daily returns)
            vol = window.std()
            
            if pd.isna(vol) or vol == 0:
                continue
                
            # Weight is inversely proportional to volatility
            weights[ticker] = 1.0 / vol
            
        # Normalize weights so they sum to exactly 1
        total_weight = sum(weights.values())
        if total_weight == 0:
            return {}
            
        normalized_weights = {ticker: w / total_weight for ticker, w in weights.items()}
        return normalized_weights

# Register the allocator with the shared PortfolioEngine instance
engine.register_allocator('inverse_volatility', InverseVolatilityAllocator())
