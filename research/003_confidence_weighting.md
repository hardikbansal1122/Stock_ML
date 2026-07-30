# Experiment 003 – Confidence Weighting

## Objective
Implement and evaluate a new allocation strategy that weights the Top-K selected stocks based on model confidence (prediction probability) rather than fixed equal weight or linear rank.

## Motivation
Predictions from XGBoost (`xg_proba`) represent a probability of a positive return. Stocks with a higher predicted probability should conceptually represent a higher expected return or a higher confidence trade. Allocating capital proportionally to this confidence "edge" may improve the risk-adjusted returns by sizing positions according to the strength of the signal.

## Allocation Formula

edge = max(probability − 0.5, 0)

weight = edge / Σ(edge)

## Advantages
- Deterministic and intuitive sizing based on predictive strength.
- Down-weights trades where the probability is closer to the 0.5 boundary.
- Non-negative weights ensuring long-only constraints are met.

## Benchmark Results

| Metric | Equal Weight | Linear Rank | Inverse Vol | Confidence |
|---|---|---|---|---|
| Total Return % | -18.9993 | -21.0986 | -17.9522 | -14.7182 |
| CAGR % | -10.2867 | -11.4921 | -9.6911 | -7.8745 |
| Sharpe | -0.1858 | -0.1975 | -0.1687 | -0.0902 |
| Max Drawdown % | -44.1189 | -45.5336 | -43.0513 | -39.6012 |
| Win Rate % | 48.7975 | 48.7975 | 48.7975 | 48.7975 |
| Avg Trade Return % | 0.2511 | 0.2511 | 0.2511 | 0.2511 |
| Number of Trades | 4740 | 4740 | 4740 | 4740 |

The confidence weighting strategy outperformed all other allocation methods across all major metrics:
- Total return improved significantly to -14.7182%.
- Sharpe ratio improved from -0.1858 (Equal Weight) to -0.0902.
- Maximum drawdown was reduced to -39.60%.
The confidence-weighted allocator produced the strongest performance among the allocation methods evaluated in this benchmark. While these results are encouraging, they are based on a single backtest configuration and should be validated across additional market periods before being considered the default allocation strategy.

## Conclusion
