import pandas as pd
from portfolio_engine import BaseAllocator
from portfolio_pipeline import engine

class ConfidenceAllocator(BaseAllocator):
    """Allocator that assigns weights based on prediction confidence (xg_proba).
    
    edge = max(xg_proba - 0.5, 0)
    weight = edge / sum(edge)
    """
    
    def allocate(self, ranked_stocks, date=None, portfolio_state=None):
        if ranked_stocks is None or ranked_stocks.empty:
            return {}
            
        if 'xg_proba' not in ranked_stocks.columns:
            return {}
            
        # compute edge
        edges = ranked_stocks['xg_proba'].apply(lambda p: max(p - 0.5, 0) if pd.notna(p) else 0)
        total_edge = edges.sum()
        
        if total_edge == 0:
            return {}
            
        weights = {}
        for idx, row in ranked_stocks.iterrows():
            if pd.isna(row.get('xg_proba')):
                continue
            p = row['xg_proba']
            edge = max(p - 0.5, 0)
            if edge > 0:
                weights[row['Ticker']] = edge / total_edge
                
        return weights

engine.register_allocator('confidence', ConfidenceAllocator())
