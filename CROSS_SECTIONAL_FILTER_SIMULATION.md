# Cross-Sectional Rank Filter Simulation

Date: 2026-06-04

## Objective
Determine whether 20-day momentum rank is useful as:
- **Option A**: a trade filter (applied in post-processing)
- **Option B**: only as a model feature (for retraining)

## Methodology
1. Loaded 321 champion trades with momentum percentile ranks
2. Determined quartile boundaries: Q1, Median, Q3
3. Simulated three filter scenarios:
   - Filter 1: Keep trades **above Q1** (remove weakest 25%)
   - Filter 2: Keep trades **above Median** (remove weakest 50%)
   - Filter 3: Keep trades **above Q3** (remove weakest 75%)
4. For each filter, computed: trade count, win rate, pred success, avg return, portfolio return, drawdown
5. Compared vs. baseline (no filter)

## Quartile Boundaries
- Q1 (25th percentile): 0.0380
- Median (50th):        0.1148
- Q3 (75th percentile): 0.2826

## Results Summary

| Scenario | Trades | Trade % | Win Rate | Pred Succ | Avg Ret | Port Ret | Max DD |
|----------|--------|---------|----------|-----------|---------|----------|--------|
| **Baseline** | 321 | 100% | 64.2% | 72.6% | +2.62% | +27.4% | -10.2% |
| Above Q1 | 236 | 74% | 68.2% (+4.0%) | 78.8% (+6.2%) | +3.04% (+0.41%) | +27.0% (-0.4%) | -6.3% (+3.9%) |
| Above Median | 160 | 50% | 68.1% (+4.0%) | 80.6% (+8.0%) | +3.39% (+0.77%) | +20.6% (-6.8%) | -7.5% (+2.7%) |
| Above Q3 | 80 | 25% | 71.2% (+7.1%) | 83.8% (+11.2%) | +3.71% (+1.08%) | +13.0% (-14.4%) | -5.1% (+5.1%) |

## Filter Effectiveness Scores
(Higher score = more promising as a filter)

- Above Q1:  +5
- Above Median:  +5
- Above Q3:  +4

## Analysis

Best filter: **Above Q1** (score: 5)

### Key Observations
- ✓ Best filter (Above Q1) has positive score (5)
- ✓ Above Q1 keeps 74% trades with improvements
- ✓ Above Median keeps 50% trades with improvements

## Recommendation

### **FILTER LOOKS PROMISING**

Rationale: One or more CS-rank filters demonstrate meaningful improvements in trade
quality metrics (win rate, prediction success, or portfolio return) while retaining
a reasonable proportion of the trade universe. This suggests CS rank can serve as an
effective post-processing filter to improve strategy selectivity.

**Implementation**: Add CS-rank filtering in post-processing:
- Compute momentum rank on entry date
- Filter trade recommendations above chosen threshold (Q1, Median, or Q3)
- Backtest to confirm improvement on live/out-of-sample data