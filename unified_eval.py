import os
import pandas as pd
from pathlib import Path

from eval_engine import PredictionAdapter, ValidationLayer, PortfolioConstructor, ModelAgnosticSimulator

def load_price_series():
    # Mirroring step4_backtest/walkforward_validation
    DATA_DIR = Path('data')
    prices = {}
    print("Loading actual price data for return calculation...")
    if not DATA_DIR.exists():
        print("Data directory not found. Please ensure price CSVs exist in 'data/'")
        return prices

    for f in DATA_DIR.glob("*.csv"):
        try:
            p = pd.read_csv(f, index_col=0)
            p.index = pd.to_datetime(p.index)
            if 'Close' in p.columns or 'Adj Close' in p.columns:
                col = 'Adj Close' if 'Adj Close' in p.columns else 'Close'
                prices[f.stem] = p[col]
        except Exception:
            pass
    return prices

ROOT = Path('.')
# Assume ranker_preds.csv has both classifier_score and ranker_score as noted in previous diagnostics
PREDS_FILE = ROOT / 'ranker_preds.csv'
REPORT_MD = ROOT / 'UNIFIED_EVALUATION_REPORT.md'

def evaluate_predictions(predictions, model_name, prices, k_values, pct_values):
    print(f"\nEvaluating {model_name}...")
    ValidationLayer.validate_predictions(predictions)
    
    results = []
    
    for k in k_values:
        print(f"  Simulating Top-{k} Portfolio...")
        trades = PortfolioConstructor.construct_top_k_trades(predictions, prices, k)
        port, cagr, sharpe, max_dd, win_rate, avg_ret, num_trades = ModelAgnosticSimulator.simulate(trades, prices)
        
        results.append({
            'Model': model_name,
            'Strategy': f'Top-{k}',
            'CAGR': cagr,
            'Sharpe': sharpe,
            'Max Drawdown': max_dd,
            'Win Rate': win_rate,
            'Avg Trade Ret': avg_ret,
            'Total Trades': num_trades
        })
        
    for pct in pct_values:
        strategy_label = f"Top-{int(pct*100)}%"
        print(f"  Simulating {strategy_label} Portfolio...")
        trades = PortfolioConstructor.construct_top_pct_trades(predictions, prices, pct)
        port, cagr, sharpe, max_dd, win_rate, avg_ret, num_trades = ModelAgnosticSimulator.simulate(trades, prices)
        
        results.append({
            'Model': model_name,
            'Strategy': strategy_label,
            'CAGR': cagr,
            'Sharpe': sharpe,
            'Max Drawdown': max_dd,
            'Win Rate': win_rate,
            'Avg Trade Ret': avg_ret,
            'Total Trades': num_trades
        })
        
    return results

def main():
    if not PREDS_FILE.exists():
        print(f"Error: Predictions file {PREDS_FILE} not found.")
        return

    print("Loading predictions and prices...")
    df = pd.read_csv(PREDS_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    prices = load_price_series()
    
    # 1. Adapt both models
    print("\nAdapting predictions...")
    try:
        clf_preds = PredictionAdapter.adapt_classifier(df)
        rnk_preds = PredictionAdapter.adapt_ranker(df)
    except Exception as e:
        print(f"Error adapting predictions: {e}")
        return
    
    k_values = [5, 10, 20]
    pct_values = [0.05, 0.10]
    
    # 2. Evaluate
    clf_results = evaluate_predictions(clf_preds, "XGBClassifier", prices, k_values, pct_values)
    rnk_results = evaluate_predictions(rnk_preds, "XGBRanker", prices, k_values, pct_values)
    
    # 3. Combine and report
    all_results = clf_results + rnk_results
    res_df = pd.DataFrame(all_results)
    
    # Format
    format_dict = {
        'CAGR': '{:.2%}', 
        'Sharpe': '{:.2f}', 
        'Max Drawdown': '{:.2%}',
        'Win Rate': '{:.2%}', 
        'Avg Trade Ret': '{:.2%}', 
        'Total Trades': '{:d}'
    }
    
    formatted_df = res_df.copy()
    for col, fmt in format_dict.items():
        formatted_df[col] = formatted_df[col].apply(lambda x: fmt.format(x))
        
    print("\nUnified Evaluation Results:")
    print(formatted_df.to_string(index=False))
    
    # Save Report
    md = "# Unified Evaluation Framework Results\n\n"
    md += "This report compares the Classifier and Ranker using identical Top-K and Top-Percentile portfolio selection criteria. "
    md += "All model-specific confidence thresholds have been removed. Both models are evaluated strictly on their ranking capability per day.\n\n"
    
    md += "## Portfolio Metrics\n\n"
    cols = formatted_df.columns.tolist()
    md += "|" + "|".join(cols) + "|\n"
    md += "|" + "|".join(["---"] * len(cols)) + "|\n"
    for _, row in formatted_df.iterrows():
        md += "|" + "|".join(str(row[c]) for c in cols) + "|\n"
        
    with open(REPORT_MD, 'w') as f:
        f.write(md)
        
    res_df.to_csv("unified_evaluation_results.csv", index=False)
    print(f"\nReport saved to {REPORT_MD.name}")
    print("Results saved to unified_evaluation_results.csv")

if __name__ == "__main__":
    main()
