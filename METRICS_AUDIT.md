# Metrics Audit

**Audit Date:** June 02, 2026

Sources used:
- `CURRENT_CHAMPION.md` (workspace)
- `RESEARCH_NOTES.md` (workspace)
- `backtest_trades.csv` (official backtest trades)
- `exit_rule_comparison.csv` (champion vs TP3 experiment results)
- `PREDICTION_SUCCESS_DEEP_DIVE.md` (diagnostic report)

---

## Computed (ground-truth) metrics (from files)

- Total trades (rows in `backtest_trades.csv`): **291**
- Prediction successes (HitPlus2Pct == 1): **205** (70.4%)
- Prediction success + financial win (HitPlus2Pct==1 and NetReturn>0): **172**
- Prediction success + financial loss (HitPlus2Pct==1 and NetReturn<0): **33**
- Failed predictions (HitPlus2Pct==0 and NetReturn<0): **77**

- Champion (from `exit_rule_comparison.csv`):
  - Portfolio Return: **+18.9726%** (displayed as +19.0%)
  - Max Drawdown: **-11.1848%** (displayed as -11.2%)
  - Win Rate (trades marked Won in `backtest_trades.csv`): **62.1993%** (displayed 62.2%)

- TP3 experiment (from `exit_rule_comparison.csv`):
  - Portfolio Return: **-6.5604%** (displayed as -6.6%)
  - Max Drawdown: **-18.2945%** (displayed as -18.3%)
  - Win Rate (TP3 trades marked Won column in experimental trades): **69.7595%**

---

## Values reported in documentation

`CURRENT_CHAMPION.md` (selected entries)
- Return: **+19.0%**
- Drawdown: **-11.2%**
- Win Rate: **62.2%**
- Trades: **291**

Prediction Quality (in `CURRENT_CHAMPION.md`)
- Prediction Success Rate: **70.4%**
- Financial Win Rate: **62.2%**
- Prediction Success + Win: **206 trades**  <-- (documented)
- Prediction Success + Loss: **33 trades**
- Failed Predictions: **52 trades**

`RESEARCH_NOTES.md` (selected entries)
- Total Trades: **291**
- Financial Winners: **181 (62.2%)**
- Prediction Successes: **205 (70.4%)**
- Prediction Success + Win: **205** (this statement appears erroneous in context)
- Prediction Success + Loss: **33 (11.3%)**
- Failed Predictions: **52 (17.9%)**

`PREDICTION_SUCCESS_DEEP_DIVE.md` (selected entries)
- Trade count: **33** (this file focuses on the subset Pred Success + Loss)
- Average MaxGainDuringHold: **+4.11%**
- Median MaxGainDuringHold: **+3.75%**
- Average BestDayReturn: **+4.22%**
- Average NetReturn (exit): **-3.00%**

`exit_rule_comparison.csv` (experiment source)
- Champion Return: **+18.9726%**
- Champion Drawdown: **-11.1848%**
- Champion Win Rate: **62.1993%**
- TP3 Return: **-6.5604%**
- TP3 Drawdown: **-18.2945%**
- TP3 Win Rate: **69.7595%**

---

## Inconsistencies and notes

1. Prediction Success + Win (documented) vs computed
   - `CURRENT_CHAMPION.md` claims **206** trades for "Prediction Success + Win".
   - Computed value from `backtest_trades.csv` is **172**.
   - `RESEARCH_NOTES.md` also contains an inconsistent line: "Prediction Success + Win: 205 (included in 181)" which is logically inconsistent.
   - Action: documentation is incorrect — both `CURRENT_CHAMPION.md` and `RESEARCH_NOTES.md` should be updated to show **172** for "Prediction Success + Win".

2. Failed Predictions count
   - `CURRENT_CHAMPION.md` and `RESEARCH_NOTES.md` report **52** failed predictions.
   - Computed failed predictions (HitPlus2Pct==0 and NetReturn<0) is **77**.
   - Likely cause: different definition used when authoring docs (they may have defined "failed" differently). Clarify canonical definition (we used HitPlus2Pct==0 & NetReturn<0).

3. TP3 win rate discrepancy
   - `RESEARCH_NOTES.md` lists TP3 win rate as **81.4%** in the narrative, but `exit_rule_comparison.csv` (the actual experiment output) shows **69.76%**.
   - `CURRENT_CHAMPION.md` and `RESEARCH_NOTES.md` correctly report TP3 return and drawdown (approx -6.6% and -18.3%), but the win-rate figure in `RESEARCH_NOTES.md` is inconsistent with the saved experimental CSV.
   - Action: update `RESEARCH_NOTES.md` to reflect actual TP3 win rate **69.76%**, or note the different win-rate calculation if intentional (e.g., whether it used modified 'Won' column vs simulation P&L classification).

4. Champion return/drawdown/win-rate
   - These are consistent across `CURRENT_CHAMPION.md`, `RESEARCH_NOTES.md`, and `exit_rule_comparison.csv` (rounded differences only). No action required.

5. Prediction Success total
   - Both docs and computed value match: **205** prediction successes (70.4% of 291). Good.

6. Prediction Success + Loss
   - Documented as **33** and computed as **33** — consistent.

7. PREDICTION_SUCCESS_DEEP_DIVE.md
   - Focuses on the 33 trades; its metrics (avg max gain, best day return, avg exit net) are consistent with the computed subset.

---

## Recommendations

- Correct `CURRENT_CHAMPION.md` and `RESEARCH_NOTES.md` to fix the following numeric inaccuracies:
  - "Prediction Success + Win": change to **172** (computed)
  - "Failed Predictions": change to **77** (computed) or clarify the doc's definition of failed predictions if a different filter was intended
  - In `RESEARCH_NOTES.md`, correct TP3 win rate to **69.76%** (or annotate if a different calculation was intentional)

- Add a short note in documentation clarifying definitions used:
  - "Prediction Success" = `HitPlus2Pct == 1` (touched +2% during hold)
  - "Winner" = `NetReturn > 0` (profitable at exit)
  - "Failed Prediction" = `HitPlus2Pct == 0 and NetReturn < 0` (model missed and trade lost)

- If any doc numbers were computed from interim outputs (e.g., earlier code versions), re-run the official `step4_backtest.py` and regenerate docs programmatically to avoid manual transcription errors.

---

If you want, I can: generate a patched PR or diff that updates `CURRENT_CHAMPION.md` and `RESEARCH_NOTES.md` to the computed numbers and add a short "Definitions" section. Would you like me to proceed with that? 
