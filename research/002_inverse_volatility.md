# Experiment 002 — Inverse Volatility Allocation

## Status

✅ Accepted

---

## Objective

Evaluate whether sizing portfolio positions inversely proportional to recent historical volatility improves portfolio-level performance compared to Equal Weight allocation.

The hypothesis was that lower-volatility stocks should receive larger allocations, reducing overall portfolio risk while preserving returns.

---

## Methodology

### Allocator

Inverse Volatility

Weight formula:

weight_i ∝ 1 / σ_i

where:

- σ_i = rolling 20-day historical volatility
- daily returns computed from adjusted closing prices
- weights normalized to sum to exactly 1

---

## Benchmark Setup

Portfolio Construction:

- Top-K Portfolio
- K = 10

Simulation:

- Same prediction model
- Same trade universe
- Same execution logic
- Same transaction costs
- Same holding period

Only the portfolio weighting methodology was changed.

---

## Validation

During validation a benchmark bug was discovered.

### Issue

The allocator was originally computing weights across the entire prediction universe (~500 stocks/day), while the simulator executed trades only for the Top-K portfolio.

This caused:

- approximately 98.6% cash allocation
- artificially tiny drawdowns
- misleading benchmark results

### Resolution

The benchmark was corrected so that:

Top-K Selection

↓

Allocator

↓

Simulator

All allocators now operate on the identical traded portfolio.

---

## Results

| Metric | Equal Weight | Inverse Volatility |
|---------|-------------:|-------------------:|
| Total Return | -18.9993% | -17.9522% |
| CAGR | -10.2867% | -9.6911% |
| Sharpe | -0.1858 | -0.1687 |
| Max Drawdown | -44.1189% | -43.0513% |

Trade-level statistics remained unchanged:

- Win Rate: identical
- Average Trade Return: identical
- Number of Trades: identical

This confirms that the improvement resulted solely from better capital allocation.

---

## Conclusion

Inverse Volatility Allocation produced consistent improvements across all evaluated portfolio metrics:

- Higher portfolio return
- Better CAGR
- Better Sharpe ratio
- Lower maximum drawdown

Although the improvements are modest, they are statistically plausible and arise from portfolio construction rather than prediction quality.

The allocator is accepted as the new portfolio sizing baseline for future experiments.

---

## Lessons Learned

The benchmark validation step identified an important evaluation flaw before conclusions were drawn.

Future allocator research should always verify:

- identical trade universe
- identical execution logic
- identical capital deployment
- only one experimental variable changed

---

## Next Experiment

Experiment 003

Confidence-Weighted Allocation

Hypothesis:

Allocate more capital to predictions with higher model confidence while preserving the existing Top-K portfolio selection.