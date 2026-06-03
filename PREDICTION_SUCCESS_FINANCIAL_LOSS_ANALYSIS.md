# Prediction Success, Financial Loss Analysis

## Summary

This report analyzes trades that **predicted correctly** (touched +2% during hold) but **finished at a loss** when exiting on day 5.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **Total Trades** | 33 |
| **Average MaxGainDuringHold** | +4.11% |
| **Median MaxGainDuringHold** | +3.75% |
| **Average BestDayReturn** | +4.22% |
| **Touched +3% during hold** | 22 trades (66.7%) |
| **Touched +5% during hold** | 9 trades (27.3%) |

---

## Interpretation

These 33 trades represent a **missed opportunity** pattern:
- The model correctly identified an intraday bullish setup (70.4% of all 75% trades touched +2%)
- Prices went **up during the 5-day hold** (average intraday gain of +4.11%)
- But exited **in the red** due to mean reversion or late-day sell-offs
- **Average financial loss: -2.27%** per trade (intraday gain turned negative by exit)

### Why This Happens

1. **Mean Reversion**: Strong intraday moves (+3% to +9%) often fade by day 5
2. **Slippage & Costs**: Entry slippage and exit costs (-0.3%) eat away small gains
3. **Timing Risk**: Day 5 exit may hit a temporary low after the intraday run

---

## Top 20 Trades by Maximum Intraday Gain

| Rank | Ticker | Entry Date | Net Return | Max Gain During Hold |
|------|--------|------------|------------|----------------------|
| 1 | VOLTAS | 2026-03-20 | -0.42% | +9.40% |
| 2 | NEOGEN | 2025-03-03 | -9.36% | +9.18% |
| 3 | BEML | 2025-03-03 | -2.46% | +7.12% |
| 4 | BAJFINANCE | 2026-03-19 | -3.79% | +6.29% |
| 5 | DEVYANI | 2026-03-09 | -2.78% | +5.76% |
| 6 | HOMEFIRST | 2024-10-04 | -2.35% | +5.59% |
| 7 | TIINDIA | 2024-11-14 | -0.34% | +5.27% |
| 8 | SAPPHIRE | 2026-03-13 | -5.56% | +5.18% |
| 9 | VOLTAS | 2026-03-23 | -5.42% | +5.12% |
| 10 | TEXRAIL | 2025-02-14 | -0.20% | +4.82% |
| 11 | AMBER | 2026-03-23 | -2.94% | +4.56% |
| 12 | ULTRACEMCO | 2026-03-23 | -1.64% | +4.09% |
| 13 | BAJFINANCE | 2026-03-23 | -2.91% | +3.98% |
| 14 | IDFCFIRSTB | 2026-03-13 | -4.39% | +3.90% |
| 15 | COROMANDEL | 2026-03-23 | -3.49% | +3.88% |
| 16 | CHOLAFIN | 2026-03-23 | -4.71% | +3.87% |
| 17 | AUBANK | 2026-03-23 | -1.35% | +3.75% |
| 18 | APTUS | 2026-03-23 | -0.74% | +3.46% |
| 19 | MPHASIS | 2025-02-28 | -0.32% | +3.43% |
| 20 | VOLTAS | 2026-03-19 | -4.20% | +3.34% |

---

## Observations

1. **Intraday accuracy is strong**: 66.7% touched +3%, showing model captures real bullish setups
2. **Exit timing is the issue**: 5-day hold exits during pullbacks/retracements
3. **VOLTAS appears 3 times** in top 20 (2026-03-19, 2026-03-20, 2026-03-23) — stock may have high intraday volatility
4. **Best performers still negative**: Even VOLTAS #1 (best gain +9.40%) ended -0.42%
5. **Opportunity**: Could consider:
   - Early profit-taking (exit at +2% to +3% hit instead of day 5)
   - Trailing stop-loss at 50% of intraday peak
   - Separate short-term vs. medium-term model

---

## Date Range

- **Earliest Trade**: 2024-10-04 (HOMEFIRST)
- **Latest Trades**: 2026-03-23 (cluster of March trades)
- **Peak Period**: March 2026 (9 trades in top 20 from March 2026)
