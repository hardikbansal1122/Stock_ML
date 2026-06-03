# Classifier-Regressor Alignment Report

**Generated:** 2026-06-02

This report compares classifier confidence and regressor-predicted return alignment for every available prediction in `test_predictions.csv`.

## Categories defined

- **High confidence, positive predicted return**: `xg_proba >= 0.75` and `pred_return > 0`
- **High confidence, negative predicted return**: `xg_proba >= 0.75` and `pred_return <= 0`
- **Low confidence, positive predicted return**: `xg_proba < 0.75` and `pred_return > 0`
- **Low confidence, negative predicted return**: `xg_proba < 0.75` and `pred_return <= 0`

All predictions were evaluated using the same 5 trading day hold window and transaction cost assumptions used by the backtest scripts.

## Category metrics

| Category | Predictions | Win rate | Prediction success | Avg net return | Avg predicted return |
|---------:|-----------:|---------:|-------------------:|---------------:|---------------------:|
| High confidence, positive predicted return | 291 | 60.48% | 71.13% | +3.0% | +3.0% |
| High confidence, negative predicted return | 0 | n/a | n/a | n/a | n/a |
| Low confidence, positive predicted return | 57,562 | 46.14% | 42.29% | -0.2% | +0.6% |
| Low confidence, negative predicted return | 26,604 | 42.96% | 38.35% | -0.6% | -0.5% |

## Key findings

1. **High-confidence predictions are strongly aligned.**
   - Every high-confidence prediction in the dataset also had a positive regressor forecast.
   - There are no high-confidence predictions with a negative predicted return.

2. **High confidence improves both classification and financial outcomes.**
   - The high-confidence positive group has the highest win rate (60.5%) and the highest prediction success rate (71.1%).
   - It also delivers the only positive average net return among the categories.

3. **Low-confidence predictions are much weaker.**
   - Both low-confidence buckets have win rates below 50%.
   - The low-confidence positive-return group still loses money on average after costs.
   - Low-confidence negative-return predictions are the weakest cohort, with average net return at -0.6%.

4. **Classifier and regressor disagreement at high confidence is not observed.**
   - In this prediction set, the classifier did not generate any high-confidence signals that the regressor labeled as negative return.
   - Therefore the current top-band strategy does not appear to be fighting itself.

## Interpretations

- The 75% confidence gate is supported by the data available here: the only high-confidence category is also the only one with a positive average net return and a materially higher prediction success rate.
- Low-confidence predictions contain much larger volume, but they are lower quality and have negative expected net return after typical cost assumptions.
- The regressor adds useful information in the broader prediction set by separating low-confidence positive predictions from low-confidence negative predictions, but neither low-confidence category is attractive on its own.

## Conclusion

- **Yes**: higher confidence corresponds with a better win rate and better actual net return in this dataset.
- **Yes**: the high-confidence group is the only category with positive average net return.
- **Yes**: the current 75% threshold is justified for the executed strategy, because it isolates the best-performing, aligned prediction cohort.
- **No strong disagreement**: the classifier and regressor are not fighting each other in the high-confidence band; they are aligned on sign.

## Notes

- This analysis uses the full `test_predictions.csv` prediction set, with actual 5-day hold outcomes derived from the available stock price history.
- If higher-confidence negative predicted-return cases are introduced later, a separate disagreement analysis should revisit the same categories.
