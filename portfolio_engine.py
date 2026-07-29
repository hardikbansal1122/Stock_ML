import abc
import typing
import pandas as pd
import numpy as np

class BaseAllocator(abc.ABC):
    """
    Abstract base class for all portfolio allocation strategies.
    """
    @abc.abstractmethod
    def allocate(
        self, 
        ranked_stocks: pd.DataFrame, 
        date: typing.Optional[str] = None, 
        portfolio_state: typing.Optional[dict] = None
    ) -> typing.Dict[str, float]:
        """
        Allocate weights to stocks.
        
        Args:
            ranked_stocks: DataFrame of predictions/rankings containing at least 'Ticker' and 'Rank'
            date: Current date string/datetime (optional)
            portfolio_state: Dictionary of current portfolio state (optional)
            
        Returns:
            Dictionary mapping Ticker to allocated weight (float).
        """
        pass


class EqualWeightAllocator(BaseAllocator):
    """
    Allocates an equal fixed weight to the top K ranked stocks.
    This exactly replicates the legacy simulator's implicit equal weighting strategy.
    """
    def __init__(self, position_size: float = 0.10, max_positions: int = 10):
        self.position_size = position_size
        self.max_positions = max_positions

    def allocate(
        self, 
        ranked_stocks: pd.DataFrame, 
        date: typing.Optional[str] = None, 
        portfolio_state: typing.Optional[dict] = None
    ) -> typing.Dict[str, float]:
        if ranked_stocks is None or ranked_stocks.empty:
            return {}
            
        # Get top K stocks based on Rank
        top_stocks = ranked_stocks[ranked_stocks['Rank'] <= self.max_positions]
        
        # Each selected stock gets the fixed position size
        weights = {row['Ticker']: self.position_size for _, row in top_stocks.iterrows()}
        return weights


class ConstraintStack:
    """
    Pipeline for applying portfolio constraints (e.g., sector limits, liquidity, max position).
    Version 1 is a pass-through placeholder.
    """
    def __init__(self):
        self.constraints = []
        
    def add_constraint(self, constraint_fn: typing.Callable):
        self.constraints.append(constraint_fn)
        
    def apply(
        self, 
        weights: typing.Dict[str, float], 
        date: typing.Optional[str] = None, 
        portfolio_state: typing.Optional[dict] = None
    ) -> typing.Dict[str, float]:
        for constraint in self.constraints:
            weights = constraint(weights, date=date, portfolio_state=portfolio_state)
        return weights


class Renormalizer:
    """
    Normalizes a dictionary of weights to sum to a target value (default 1.0).
    Version 1 allows passing through without normalization to ensure exact backward compatibility.
    """
    def __init__(self, target_sum: float = 1.0, bypass: bool = False):
        self.target_sum = target_sum
        self.bypass = bypass
        
    def normalize(self, weights: typing.Dict[str, float]) -> typing.Dict[str, float]:
        if self.bypass or not weights:
            return weights
            
        total_weight = sum(weights.values())
        if total_weight <= 0:
            return weights
            
        scale_factor = self.target_sum / total_weight
        return {ticker: weight * scale_factor for ticker, weight in weights.items()}


class PortfolioEngine:
    """
    The main registry and entry point for Portfolio Construction.
    """
    def __init__(self, bypass_renormalization: bool = True):
        # Register standard allocators
        self._allocators: typing.Dict[str, BaseAllocator] = {
            'equal_weight': EqualWeightAllocator(position_size=0.10, max_positions=10)
        }
        
        self.constraint_stack = ConstraintStack()
        
        # By default in V1, bypass renormalization to guarantee exact legacy matches 
        # (e.g., maintaining residual cash if < 10 stocks are selected)
        self.renormalizer = Renormalizer(target_sum=1.0, bypass=bypass_renormalization)

    def register_allocator(self, strategy_name: str, allocator: BaseAllocator):
        """Register a new allocator strategy."""
        self._allocators[strategy_name] = allocator

    def allocate(
        self, 
        ranked_stocks: pd.DataFrame, 
        strategy: str = "equal_weight", 
        date: typing.Optional[str] = None, 
        portfolio_state: typing.Optional[dict] = None
    ) -> typing.Dict[str, float]:
        """
        Allocate weights for a given set of ranked stocks using the specified strategy.
        
        Args:
            ranked_stocks: DataFrame of prediction data for a single day.
            strategy: Name of the strategy (e.g., 'equal_weight').
            date: Optional date string/datetime.
            portfolio_state: Optional dictionary containing current holdings, cash, etc.
            
        Returns:
            Dictionary mapping Tickers to allocated weight (float).
        """
        if strategy not in self._allocators:
            raise ValueError(
                f"Unknown allocation strategy: '{strategy}'. "
                f"Registered strategies are: {list(self._allocators.keys())}"
            )
            
        allocator = self._allocators[strategy]
        
        # 1. Base Allocation
        weights = allocator.allocate(ranked_stocks, date=date, portfolio_state=portfolio_state)
        
        # 2. Apply Constraints
        weights = self.constraint_stack.apply(weights, date=date, portfolio_state=portfolio_state)
        
        # 3. Renormalize (if not bypassed)
        weights = self.renormalizer.normalize(weights)
        
        return weights
