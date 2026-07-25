# Alpha101 Feature Gap Report vs. Current XGBoost Feature Pipeline

## Executive summary

Your current feature engineering pipeline is already strong on the basic building blocks that matter for a tree-based model such as XGBoost:

- short-horizon and medium-horizon momentum
- simple moving-average and crossover signals
- RSI-style oscillator behavior
- rolling volatility and range-based risk proxies
- volume spike and relative-volume proxies
- benchmark-relative context via Nifty features
- a simple cross-sectional momentum rank

That means the pipeline already captures a solid “first-generation” set of alpha-style signals. The main gap is not raw signal variety; it is the lack of more sophisticated Alpha101-style families that are more orthogonal to your current features and more likely to add incremental predictive power.

For your current XGBoost setup, the biggest upside is likely to come from factors that are:

1. statistically robust rather than purely noisy
2. less redundant with your current momentum and volatility features
3. more explicitly market-neutral or cross-sectional
4. relatively cheap to compute and easy to maintain

---

## 1) Alpha101-style factors already represented by your current features

The current pipeline already covers several important Alpha101 families in spirit, even if the exact formulas are not identical.

| Alpha101-style family | Current pipeline features | Assessment |
|---|---|---|
| Short-term momentum | ret_1d, ret_3d, ret_5d, ret_10d, ret_20d | Strongly represented |
| Medium-term trend / crossover | ma5_vs_ma20, ma10_vs_ma50, price_vs_ma5, price_vs_ma20, price_vs_ma50 | Strongly represented |
| Oscillator / overbought-oversold | rsi14, rsi_normalized | Strongly represented |
| Volatility / risk | volatility_5d, volatility_20d, hl_range | Strongly represented |
| Volume spike / relative volume | volume_ratio, volume_trend, relative_volume, updown_vol_ratio_10 | Strongly represented |
| Trend persistence / directional consistency | up_days_5, up_days_10, momentum_acceleration | Moderately represented |
| Market-regime context | nifty_ret_5d, nifty_ret_20d, nifty_above_ma50, nifty_rsi14, nifty_volatility_20d, nifty_price_vs_ma200, nifty_ma50_vs_ma200 | Strongly represented |
| Relative-strength vs market | rs_ret_5d, rs_ret_20d, rs_ret_60d, rs_acceleration, momentum_persistence | Strongly represented |
| Cross-sectional momentum | cs_rank_20d | Represented |
| Gap / overnight effect | gap | Represented |

### Practical interpretation

Your current pipeline is already good at capturing:

- momentum
- trend-following
- simple mean-reversion proxies
- volatility and volume shocks
- benchmark-relative strength

What it is not yet doing very well is introducing more sophisticated, less redundant alpha families that can add information beyond these broad primitives.

---

## 2) Alpha101-style factors that are completely missing or only weakly represented

The most obvious gaps are below.

### A. VWAP deviation factors

Missing or very weakly represented.

Why it matters:
- VWAP-based signals often capture whether price is trading above or below the average execution price, which can be a strong short-term signal.
- It is conceptually different from a simple moving average and often provides cleaner intraday context.

### B. Standardized mean-reversion z-scores

Partially present, but not in the more robust Alpha101-style form.

Why it matters:
- Your current features use price-vs-MA and RSI, but not a rolling z-score of price relative to a rolling mean and rolling volatility.
- That form is often more statistically meaningful and can be more stable than raw spread features.

### C. Close-to-open / overnight reversal factors

Your pipeline has a generic gap feature, but it does not explicitly separate:
- close-to-open reversals
- overnight continuation
- gap-to-close behavior

This is a meaningful omission because overnight behavior often carries information that is distinct from same-day momentum.

### D. Cross-sectional ranking with stronger normalization

You have a basic cross-sectional rank, but it is not yet:
- industry/sector-neutral
- market-cap-adjusted
- volatility-adjusted
- residualized against benchmark or sector performance

That is a major gap because cross-sectional alpha often improves dramatically when the ranking is made more neutral and robust.

### E. Volume-price interaction factors

You have volume ratio and volume trend, but not richer forms such as:
- price change conditioned on volume shock
- correlation between returns and volume over a rolling window
- volume-adjusted momentum strength

These are strong Alpha101-style candidates because they exploit information not captured by price alone.

### F. Volatility-adjusted momentum

Your pipeline includes momentum and volatility separately, but not a blended signal such as:
- momentum divided by realized volatility
- return strength normalized by recent volatility

This often improves signal quality because it penalizes noisy high-volatility moves.

### G. Residualized benchmark-relative signals

You have market-relative return features, but not a more refined residual signal that removes the common market component more aggressively.

### H. Long-short spread / rank-based reversal factors

Your features are mostly direct price/volume transforms, not explicitly “ranked” and “cross-sectionalized” in the Alpha101 sense.

---

## 3) Missing factors most likely to provide the highest incremental information

The missing factors below are most likely to add incremental value for your current XGBoost model.

### 1. Cross-sectional rank of return relative to benchmark or sector

Why this is high value:
- XGBoost often benefits from relative ranking signals, especially when the universe is large.
- A simple cross-sectional rank already exists, but a more neutral version would likely be more informative.

Expected impact: High

### 2. Rolling z-score mean reversion around a rolling mean and volatility

Why this is high value:
- This is one of the most classic and robust alpha formulations.
- It is easier to interpret and often more stable than raw spread features.

Expected impact: High

### 3. VWAP deviation

Why this is high value:
- It is a different signal family from simple moving-average deviation.
- It can be especially useful in liquid, high-frequency-style regimes.

Expected impact: Medium-high

### 4. Close-to-open reversal / overnight gap-to-close signal

Why this is high value:
- Overnight behavior often carries a different structure than same-day momentum.
- This can help the model learn micro-structure-like effects that are not captured by your current features.

Expected impact: Medium-high

### 5. Volume-price correlation or volume-adjusted momentum

Why this is high value:
- Volume often carries predictive information not visible in price alone.
- These factors are often more robust than simple volume-ratio features.

Expected impact: Medium-high

### 6. Volatility-adjusted momentum

Why this is high value:
- It reduces the tendency to overvalue noisy big-move stocks.
- This is often a strong complement to raw momentum.

Expected impact: Medium

### 7. Residual momentum against market or sector trend

Why this is high value:
- Bench-mark-relative signals are useful, but residualization makes them cleaner and more orthogonal.

Expected impact: Medium

---

## 4) Top 20 Alpha101-style factors ranked by expected usefulness for your current XGBoost model

The ranking below is practical rather than literal, because the exact Alpha101 factor IDs in the paper are not necessary for the purpose of this report. The goal is to assess which Alpha101-style families are most likely to help your current pipeline.

| Rank | Factor | What it measures | Class | Computational complexity | Overfitting risk | Expected usefulness |
|---|---|---|---|---|---|---|
| 1 | Sector-neutral cross-sectional rank of 20-day return | Whether a stock is strong relative to peers, not just relative to itself | Cross-sectional | Low | Low-medium | Very high |
| 2 | Rolling z-score of price vs 20-day mean | How far price is from its recent mean, standardized by recent volatility | Mean reversion | Low | Low | Very high |
| 3 | 20-day return residualized vs market or sector | Stock momentum after removing common market/sector movement | Cross-sectional | Low-medium | Low-medium | Very high |
| 4 | VWAP deviation | Whether price is above or below the volume-weighted average price | VWAP | Low-medium | Low | Very high |
| 5 | Close-to-open reversal | Whether opening gap reverses during the session | Mean reversion | Low | Low-medium | High |
| 6 | Volume-adjusted momentum | Whether momentum is strong after accounting for volume participation | Volume / momentum | Low-medium | Medium | High |
| 7 | Volume-price correlation over rolling window | Whether price moves are supported by volume flow | Volume | Medium | Medium | High |
| 8 | Volatility-adjusted momentum | Whether momentum is strong relative to recent realized volatility | Volatility / momentum | Low-medium | Medium | High |
| 9 | 5-day momentum with 20-day reversal interaction | Short-term continuation plus longer-term overreaction | Momentum / mean reversion | Low-medium | Medium | High |
| 10 | Overnight gap-to-close signal | Whether gap behavior predicts the next session’s close | Mean reversion | Low | Low-medium | High |
| 11 | Rank of 20-day return within market-cap bucket | Relative strength adjusted for stock size | Cross-sectional | Low-medium | Low-medium | Medium-high |
| 12 | Price distance from Bollinger band with volume confirmation | Whether price is stretched and volume confirms the move | Volatility / volume | Medium | Medium | Medium-high |
| 13 | Short-horizon reversal after strong trend | Whether a recent trend is likely to reverse quickly | Mean reversion | Low | Medium | Medium-high |
| 14 | High-low range normalized by close | Whether the daily range is unusually large | Volatility | Low | Low | Medium-high |
| 15 | 60-day reversal after strong recent move | Whether long-horizon winners are likely to fade | Mean reversion | Low | Medium | Medium |
| 16 | Momentum acceleration minus trailing momentum | Whether trend strength is improving or weakening | Momentum | Low | Low-medium | Medium |
| 17 | Price-to-EMA deviation | Whether price is far from the exponential moving average | Mean reversion / trend | Low | Low | Medium |
| 18 | Rank of volume trend relative to peers | Whether a stock is gaining participation relative to peers | Volume / cross-sectional | Medium | Medium | Medium |
| 19 | Return correlation with benchmark over rolling window | Whether a stock’s moves are becoming more market-like | Cross-sectional / market regime | Medium | Medium | Medium |
| 20 | Turnover-adjusted return | Whether price move is large relative to trading activity | Volume / turnover | Medium | Medium | Medium |

---

## 5) Best 10 factors to implement first

If the goal is to improve your current XGBoost model without overcomplicating the pipeline, the best first 10 are the following.

### Recommended first 10

1. Sector-neutral cross-sectional rank of 20-day return
2. Rolling z-score of price versus 20-day mean
3. 20-day return residualized versus Nifty or sector
4. VWAP deviation
5. Close-to-open reversal
6. Volume-adjusted momentum
7. Volume-price correlation over a rolling window
8. Volatility-adjusted momentum
9. 5-day momentum with 20-day reversal interaction
10. Overnight gap-to-close signal

### Why these 10 are the best first choices

They give the best balance of:

- strong predictive value
- low-to-moderate implementation difficulty
- decent robustness
- meaningful difference from your current features

They are also likely to be more orthogonal to the existing pipeline than simply adding more raw return lags or more moving-average variants.

---

## Bottom line

Your pipeline already covers a strong base of momentum, trend, volatility, volume, and market-context features. That is a good foundation.

The biggest opportunity is not to add more generic return lags. It is to add Alpha101-style factors that are more:

- cross-sectional
- benchmark-neutral
- standardized and statistically robust
- volume-aware
- explicitly mean-reverting or VWAP-based

If the goal is to improve your XGBoost model with the least noise, the highest-priority additions are cross-sectional ranking, z-score-based mean reversion, VWAP deviation, close-to-open signals, and volume-adjusted momentum.
