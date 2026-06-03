# Confidence Calibration Report

**Generated:** 2026-06-02

This report analyzes classifier confidence calibration using the final backtest trade dataset `backtest_trades.csv`.

> Note: `backtest_trades.csv` contains only the selected trades from the final simulation. Because the current strategy only executed trades at 75% confidence or above, the lower confidence buckets contain zero trades in this dataset.

## Bucket metrics

| Confidence bucket | Trades | Win rate | Prediction success | Avg net return | Avg predicted return |
|------------------:|-------:|---------:|-------------------:|---------------:|---------------------:|
| 50-55% | 0 | n/a | n/a | n/a | n/a |
| 55-60% | 0 | n/a | n/a | n/a | n/a |
| 60-65% | 0 | n/a | n/a | n/a | n/a |
| 65-70% | 0 | n/a | n/a | n/a | n/a |
| 70-75% | 0 | n/a | n/a | n/a | n/a |
| 75-80% | 248 | 63.3% | 69.4% | +2.2% | +2.8% |
| 80-85% | 40 | 60.0% | 80.0% | +2.2% | +3.7% |
| 85-90% | 3 | 0.0% | 33.3% | -3.3% | +4.1% |
| 90%+ | 0 | n/a | n/a | n/a | n/a |

## Calibration analysis

- The current backtest dataset has no trades below 75% confidence, so the lower buckets cannot be calibrated from these executed signals.
- Within the observed buckets, higher confidence does not clearly translate to a higher win rate:
  - 75-80%: 63.3% win rate
  - 80-85%: 60.0% win rate
  - 85-90%: 0.0% win rate (only 3 trades)
- Prediction success rate is higher in the 80-85% bucket than the 75-80% bucket, but the sample size for 85-90% is too small to draw reliable conclusions.
- Average predicted return increases with confidence among observed buckets, from +2.8% to +3.7% to +4.1%.
- Average net return is flat across the two larger buckets (75-80% and 80-85%) at +2.2%, and the 85-90% bucket is negative, but that bucket has only 3 trades.

## Answers to the requested questions

### Does higher confidence actually mean higher win rate?
Not consistently in this dataset. The 80-85% bucket has a slightly lower win rate than 75-80%, and the 85-90% bucket has zero wins, though its sample is very small.

### Does higher confidence mean higher returns?
Predicted returns do increase with confidence in the observed buckets. Actual net returns are similar for 75-80% and 80-85%, and the tiny 85-90% bucket is negative, so stronger evidence is needed before assuming higher confidence reliably means higher realized return.

### Are there confidence ranges that should be avoided?
From this dataset:
- The 85-90% bucket is too small to support a reliable decision; it produced only 3 trades and a negative average net return.
- No inference can be made for buckets below 75% because they were not represented in the executed trade set.

### Is the current 75% threshold justified?
The current threshold is defensible as a practical cutoff for this backtest because all executed trades were at 75% or higher. That said, the data do not prove that a higher threshold would improve win rate or net return. A broader evaluation using all candidate predictions (including non-executed lower-confidence signals) would be required to determine whether 75% is the optimal threshold.

## Recommendation

- Keep 75% as the operational threshold for now, but treat the evidence as limited to the executed signal set.
- Collect and analyze lower-confidence predictions separately if you want to validate whether the model is truly calibrated across the full 50-90% range.
- Use larger sample sizes before drawing conclusions about 85%+ predictions.
