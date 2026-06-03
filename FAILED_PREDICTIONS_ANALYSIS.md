# Failed Predictions Analysis


**Report Date:** 2026-06-02


## Filter: `TradeCategory == "Failed Prediction"`


### 1) Count
- Total failed-prediction trades: **77**


### 2) Average NetReturn
- Average NetReturn: **-0.0516%**


### 3) Worst 20 trades (by NetReturn)


| Rank | Ticker | EntryDate | NetReturn | PredictionProb | Notes |
|---:|---|---|---:|---:|---|
| 1 | KAYNES | 2025-01-22 | -0.1585 | 0.7875772 |  |
| 2 | MIDHANI | 2026-03-19 | -0.1452 | 0.7653371 |  |
| 3 | YATHARTH | 2025-01-13 | -0.1281 | 0.7904296 |  |
| 4 | AVALON | 2025-01-22 | -0.1253 | 0.7927179 |  |
| 5 | TEXRAIL | 2026-03-19 | -0.1238 | 0.7682727 |  |
| 6 | KIOCL | 2025-02-11 | -0.1109 | 0.76364523 |  |
| 7 | BANDHANBNK | 2026-03-19 | -0.1109 | 0.7555497 |  |
| 8 | BEML | 2024-08-06 | -0.1109 | 0.7746552 |  |
| 9 | RPOWER | 2024-10-04 | -0.1036 | 0.76149434 |  |
| 10 | NETWORK18 | 2025-01-13 | -0.1031 | 0.7859636 |  |
| 11 | CANBK | 2026-03-19 | -0.0982 | 0.75534254 |  |
| 12 | FACT | 2025-03-06 | -0.0979 | 0.76052296 |  |
| 13 | DEVYANI | 2026-03-19 | -0.0950 | 0.81102043 |  |
| 14 | INOXWIND | 2026-03-19 | -0.0806 | 0.78963375 |  |
| 15 | BANKBARODA | 2026-03-23 | -0.0804 | 0.79592407 |  |
| 16 | HINDCOPPER | 2026-03-19 | -0.0764 | 0.82268727 |  |
| 17 | APTUS | 2026-03-19 | -0.0713 | 0.77879137 |  |
| 18 | BEML | 2025-02-19 | -0.0678 | 0.7545464 |  |
| 19 | KPITTECH | 2026-03-04 | -0.0675 | 0.75808936 |  |
| 20 | HDFCLIFE | 2026-03-23 | -0.0642 | 0.7977875 |  |


### 4) Distribution by confidence bucket
- 75-80: 68
- 80-85: 7
- 85+: 2
- <75: 0


### 5) Distribution by month
- 2024-08: 1
- 2024-10: 6
- 2024-11: 4
- 2025-01: 12
- 2025-02: 9
- 2025-03: 1
- 2026-02: 2
- 2026-03: 42


### 6) Distribution by market regime (if available)
- Market regime column not found in trades; distribution unavailable


### 7) Common characteristics


Top differing numeric metrics (failed vs overall):


| Metric | Failed Mean | Overall Mean | % Difference |
|---|---:|---:|---:|
| NetReturn | -0.0516 | 0.0215 | -340.15% |
| GrossReturn | -0.0486 | 0.0245 | -298.46% |
| MaxAdverseExcursion | -0.0672 | -0.0299 | -124.48% |
| LoserButProfitableIntraday | 0.5065 | 0.2474 | 104.71% |
| Won | 0.0000 | 0.6220 | -100.00% |
| HitPlus2Pct | 0.0000 | 0.7045 | -100.00% |
| HitPlus3Pct | 0.0000 | 0.6186 | -100.00% |
| HitPlus5Pct | 0.0000 | 0.4708 | -100.00% |


- No sector/industry column available


### 8) Recommendations: Which trades should be filtered out?


- Consider stricter confidence cutoff: the 75-80 bucket accounts for 68 failed trades (88.3% of failed predictions).
- Filter trades in months with high failure concentration (see month distribution).
- If market regime data becomes available, filter regimes with disproportionate failures.
- Consider excluding specific sectors with repeated failures (if sector data found).
- Consider additional filters: high intraday peak-to-exit reversal (MaxGainDuringHold high but NetReturn negative), low liquidity tickers, or large negative skew in returns.