# Learning-to-Rank Evaluation (Phase 2)

## Performance Comparison

|index|NDCG@5|NDCG@10|P@5|P@10|P@20|MRR|Lift|CAGR|Sharpe|Max Drawdown|Win Rate|Avg Trade Ret|Trades|ROC-AUC|PR-AUC|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|XGBClassifier|0.3386|0.3421|33.7%|34.3%|33.9%|0.5254|1.09x|0.0%|0.00|0.0%|0.0%|0.00%|0|0.5327|0.3655|
|XGBRanker|0.3818|0.3785|37.9%|37.5%|37.6%|0.5764|1.17x|0.0%|0.00|0.0%|0.0%|0.00%|0|0.5548|0.3689|

## Architecture Differences
- **Classifier**: `binary:logistic`. Optimizes for global probability (log-loss) across the entire dataset.
- **Ranker**: `rank:ndcg`. Optimizes for relative ordering (pairwise/listwise) per day using query groups.

## Training Procedure
Both models were trained using exactly the same 14 features on a 24-month rolling window with a 3-month test period. The ranker required grouping samples by `Date` via a `qid` column.

## Recommendation
*(See data above to evaluate)*

