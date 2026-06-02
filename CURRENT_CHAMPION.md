Champion Strategy

Branch:
realistic-portfolio-sim-v1

Features:
- Market regime features
- Confidence sizing
- Realistic portfolio simulator

Threshold:
75%

Performance:
Return      : +19.0%
Drawdown    : -11.2%
Win Rate    : 62.2%
Trades      : 291

Prediction Quality:
Prediction Success Rate        : 70.4%
Financial Win Rate             : 62.2%
Prediction Success + Win       : 172 trades
Prediction Success + Loss      : 33 trades
Failed Predictions             : 77 trades

Date:
May 31, 2026

Recent Research Findings:

- **Prediction accuracy is strong:** 70.4% of trades touched +2% during hold
- **Financial outcomes lag slightly:** Only 62.2% finished profitably, indicating mean reversion after intraday runs
- **Missed opportunity pattern:** 33 trades correctly predicted intraday bullish move (+2% to +9%) but exited negative on day 5
  - Average intraday peak: +4.11%
  - Average day-5 exit: -2.27%
- **Take-profit experiment (+3% exit):** Tested early exit when +3% is touched
  - Result: -6.6% portfolio return (vs +19.0% champion)
  - Verdict: Rejected — aggressive exits underperform the 5-day hold strategy

---

Documentation Status:
Last audited against:
- backtest_trades.csv
- exit_rule_comparison.csv
- latest step4_backtest.py output