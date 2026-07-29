# Portfolio Engine Implementation (Version 1)

## Architecture Overview

The new Portfolio Construction Layer introduces a modular, strategy-agnostic architecture. It is designed to act as an independent allocation engine that can plug into the existing prediction and evaluation framework without requiring upstream or downstream modifications to existing core mechanics. 

The architecture consists of four primary components:
1. **BaseAllocator & Concrete Strategies**: Defines the core allocation logic (e.g., `EqualWeightAllocator`).
2. **ConstraintStack**: A pipeline for portfolio constraints (e.g., sector limits, liquidity) which currently acts as a pass-through extension point.
3. **Renormalizer**: An extension point to scale allocations to a target sum (e.g., `1.0`). In V1, this is bypassable to allow exact mathematically matching of legacy behaviors where residual cash was preserved if insufficient signals existed.
4. **PortfolioEngine**: The central registry and execution factory that ties the components together.

## File Structure
- `portfolio_engine.py`: Contains the `PortfolioEngine`, `BaseAllocator`, `EqualWeightAllocator`, `ConstraintStack`, and `Renormalizer`.
- `verify_portfolio_engine.py`: A script verifying that the new engine's output mathematically matches the legacy `ModelAgnosticSimulator`'s internal position sizing.

## Public Interfaces
The engine is interacted with via a single clean interface:

```python
from portfolio_engine import PortfolioEngine

engine = PortfolioEngine(bypass_renormalization=True)
weights = engine.allocate(
    ranked_stocks=daily_predictions, 
    strategy="equal_weight", 
    date="2026-07-28"
)
# Returns: {'AAPL': 0.10, 'MSFT': 0.10, ...}
```

## Extension Points
The architecture is completely decoupled from the simulator and evaluation metrics, meaning new logic can be added without modifying legacy code:

### 1. Adding a New Strategy
Create a class inheriting from `BaseAllocator` and register it:
```python
class RiskParityAllocator(BaseAllocator):
    def allocate(self, ranked_stocks, date=None, portfolio_state=None):
        # ... logic ...
        return weights

engine.register_allocator('risk_parity', RiskParityAllocator())
weights = engine.allocate(ranked_stocks, strategy="risk_parity")
```

### 2. Adding Constraints
```python
def max_position_constraint(weights, **kwargs):
    return {k: min(v, 0.15) for k, v in weights.items()}

engine.constraint_stack.add_constraint(max_position_constraint)
```

## Migration Notes
The legacy `ModelAgnosticSimulator` in `eval_engine.py` dynamically sizes positions using a hardcoded `POSITION_SIZE = 0.10`. 

Because `eval_engine.py` is frozen and we cannot modify the `ModelAgnosticSimulator` to accept variable weights at this time, the Portfolio Engine is implemented as a parallel decoupled layer. 
- In this initial phase, the engine proves that it perfectly generates the mathematically equivalent `0.10` weights for the exact same subset of stocks that the `ModelAgnosticSimulator` selects.
- To fully migrate in the future, the simulator will need to be updated to consume the `weights` dictionary outputted by `PortfolioEngine.allocate()` instead of relying on its internal `POSITION_SIZE`. 

## Validation Results
- **Identical Outputs Verified**: The `verify_portfolio_engine.py` script confirms that `EqualWeightAllocator` assigns an exact `0.10` weight to the exact same list of top stocks selected by the legacy prediction step. 
- **No Simulator Changes Required**: The new engine was built as a standalone module. The existing simulator, prediction adapters, and eval framework were untouched and remain frozen.
- **Extensibility Verified**: A dummy `RiskParityAllocator` was successfully registered and executed using the new interface to verify pluggability.

## Future Roadmap (Do not implement yet)
- **RankWeightAllocator**: Weights proportional to prediction score or rank.
- **InverseVolAllocator**: Volatility scaling using standard deviation.
- **RiskParity / Black-Litterman**: Advanced covariance-based allocations.
- **Sector Constraints**: Ensure no single sector exceeds 30% allocation.
- **Simulator Integration**: Update the simulator to natively execute trades scaled exactly to the weights dictionary provided by the Portfolio Engine.
