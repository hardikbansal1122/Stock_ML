from portfolio_engine import BaseAllocator
from portfolio_pipeline import engine

class LinearRankAllocator(BaseAllocator):
    """Allocator that assigns linearly decreasing weights to the top N stocks.

    Weight for a stock of rank r (1‑based) among N selected stocks:
        w(r) = (N - r + 1) / (N * (N + 1) / 2)
    The weights sum exactly to 1.
    """

    def __init__(self, max_positions: int = 10):
        self.max_positions = max_positions

    def allocate(self, ranked_stocks, date=None, portfolio_state=None):
        # Guard against empty input
        if ranked_stocks is None or ranked_stocks.empty:
            return {}
        # Select the top‑N based on Rank
        top = ranked_stocks[ranked_stocks['Rank'] <= self.max_positions]
        n = len(top)
        # Normalisation denominator (sum of 1..n)
        denom = n * (n + 1) / 2.0 if n > 0 else 1.0
        weights = {}
        for _, row in top.iterrows():
            rank = int(row['Rank'])
            weight = (n - rank + 1) / denom
            weights[row['Ticker']] = weight
        return weights

# Register the allocator with the shared PortfolioEngine instance
engine.register_allocator('linear_rank', LinearRankAllocator())
