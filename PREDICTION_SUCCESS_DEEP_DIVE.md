# Prediction Success — Deep Dive

**Filtered set:** `TradeCategory == "Prediction Success, Financial Loss"`

1. **Trade count:** 33

2. **Distribution of MaxGainDuringHold:**

- 2%-3%: 11 trades (33.3%)
- 3%-5%: 13 trades (39.4%)
- 5%-8%: 7 trades (21.2%)
- 8%-10%: 2 trades (6.1%)
- 10%+: 0 trades (0.0%)

3. **Average MaxGainDuringHold:** +4.11%
4. **Median MaxGainDuringHold:** +3.75%
5. **Average BestDayReturn:** +4.22%
6. **Average NetReturn (exit):** -3.00%

7. **Top 20 trades by MaxGainDuringHold:**

| Rank | Ticker | Entry Date | NetReturn | MaxGainDuringHold | BestDayReturn |
|---:|:---|:---:|:---:|:---:|:---:|
| 1 | VOLTAS | 2026-03-20 | -0.42% | +9.40% | +5.12% |
| 2 | NEOGEN | 2025-03-03 | -9.36% | +9.18% | +11.29% |
| 3 | BEML | 2025-03-03 | -2.46% | +7.12% | +3.36% |
| 4 | BAJFINANCE | 2026-03-19 | -3.79% | +6.28% | +4.48% |
| 5 | DEVYANI | 2026-03-09 | -2.78% | +5.76% | +4.45% |
| 6 | HOMEFIRST | 2024-10-04 | -2.35% | +5.59% | +3.54% |
| 7 | TIINDIA | 2024-11-14 | -0.34% | +5.27% | +5.27% |
| 8 | SAPPHIRE | 2026-03-13 | -5.56% | +5.18% | +3.55% |
| 9 | VOLTAS | 2026-03-23 | -5.42% | +5.12% | +5.12% |
| 10 | TEXRAIL | 2025-02-14 | -0.20% | +4.82% | +5.61% |
| 11 | AMBER | 2026-03-23 | -2.94% | +4.56% | +4.56% |
| 12 | ULTRACEMCO | 2026-03-23 | -1.64% | +4.09% | +4.09% |
| 13 | BAJFINANCE | 2026-03-23 | -2.91% | +3.98% | +3.98% |
| 14 | IDFCFIRSTB | 2026-03-13 | -4.39% | +3.90% | +2.51% |
| 15 | COROMANDEL | 2026-03-23 | -3.49% | +3.88% | +3.88% |
| 16 | CHOLAFIN | 2026-03-23 | -4.71% | +3.87% | +3.87% |
| 17 | AUBANK | 2026-03-23 | -1.35% | +3.75% | +3.82% |
| 18 | APTUS | 2026-03-23 | -0.74% | +3.46% | +4.69% |
| 19 | MPHASIS | 2025-02-28 | -0.32% | +3.43% | +2.73% |
| 20 | VOLTAS | 2026-03-19 | -4.20% | +3.34% | +5.12% |

## Key findings

- Majority are 3%-5% movers.

- Average MaxGainDuringHold is 4.11%, median 3.75% — typical intraday peaks are a few percent.
- Average BestDayReturn is +4.22%, indicating intraday bursts often occur on a single day.
- Average NetReturn at exit is -3.00%, confirming many of these trades end negative despite intraday peaks.

- **Evidence on exit timing:** 33 trades (100.0%) touched +2% but closed negative — strong indication exit timing contributes to losses.

### Do these trades have anything in common?

- Many show a large intraday spike (MaxGainDuringHold often 3–9%) followed by a retracement before the day-5 exit.
- Several appear clustered in volatile periods (e.g., March 2026) and specific tickers show repetition (VOLTAS appears multiple times).
- Common theme: short-lived momentum that reverts within the 5-day window.

### Verdict on exit timing

- The evidence suggests exit timing is a primary issue: a sizeable share of trades reach intraday peaks but the 5-day exit captures the reversion, turning wins into losses.
- This supports experiments with earlier exit or dynamic exits (trailing stops), but our TP3 experiment showed naive +3% exit underperformed overall.