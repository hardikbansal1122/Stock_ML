# UNIFIED EVALUATION REPORT

## Final Experiment Results

|Model|Strategy|Total Trades|CAGR|Sharpe|Win Rate|Max Drawdown|Avg Trade Ret|
|---|---|---|---|---|---|---|---|
|XGBClassifier|Top-5|3060|12.90%|0.62|48.46%|-22.41%|0.24%|
|XGBClassifier|Top-10|6120|19.02%|0.85|48.58%|-24.20%|0.30%|
|XGBClassifier|Top-20|12240|16.04%|0.74|48.42%|-24.20%|0.35%|
|XGBRanker|Top-5|3060|25.91%|0.94|49.28%|-33.86%|0.51%|
|XGBRanker|Top-10|6120|26.37%|0.97|49.23%|-35.93%|0.42%|
|XGBRanker|Top-20|12240|25.38%|0.94|49.40%|-35.85%|0.46%|

## Classifier vs Ranker Comparison
The XGBRanker uniformly outperforms the XGBClassifier across Top-5, Top-10, and Top-20 portfolios in CAGR, Sharpe, and Win Rate, validating the learning-to-rank approach for relative selection.

## Recommendations
Adopt the XGBRanker model as the new baseline champion. Its objective function naturally aligns with Top-K execution strategies.