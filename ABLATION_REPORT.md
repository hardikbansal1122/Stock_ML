# Feature Ablation Framework Results

|Experiment|ROC-AUC|PR-AUC|Precision@10|NDCG|Top-Decile Lift|IC|ICIR|Win Rate|CAGR|Sharpe|Max Drawdown|Trades|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Exp 1: Baseline|0.5260|0.3640|33.3%|0.7376|1.11x|-0.0107|-0.0771|0.0%|0.0%|0.00|0.0%|0|
|Exp 2: Baseline + Market Breadth|0.5119|0.3537|34.0%|0.7361|1.06x|0.0027|0.0234|0.0%|0.0%|0.00|0.0%|0|
|Exp 3: Baseline + Market Relative|0.5387|0.3609|35.4%|0.7406|1.12x|-0.0095|-0.0679|0.0%|0.0%|0.00|0.0%|0|
|Exp 4: Baseline + Cross-Sectional Ranking|0.5395|0.3638|35.4%|0.7402|1.11x|-0.0082|-0.0586|0.0%|0.0%|0.00|0.0%|0|
|Exp 5: Baseline + 52-Week Position|0.5392|0.3678|35.9%|0.7411|1.11x|-0.0073|-0.0533|0.0%|0.0%|0.00|0.0%|0|


## Recommendation

Based on out-of-sample ROC-AUC and generalization metrics, the optimal feature set is **Exp 4: Baseline + Cross-Sectional Ranking**.
