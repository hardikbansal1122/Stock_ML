import os, sys
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)
import pandas as pd
from eval_engine import PredictionAdapter, PortfolioConstructor, ModelAgnosticSimulator
from portfolio_pipeline import run_pipeline

preds_path = os.path.join(project_root, 'test_predictions.csv')
if not os.path.exists(preds_path):
    raise FileNotFoundError(f'Predictions file not found at {preds_path}')
preds = pd.read_csv(preds_path)
preds['Date'] = pd.to_datetime(preds['Date'])

# Load price data
prices = {}
for f in os.listdir(os.path.join(project_root, 'data')):
    if f.endswith('.csv'):
        try:
            p = pd.read_csv(os.path.join(project_root, 'data', f), index_col=0)
            p.index = pd.to_datetime(p.index)
            col = 'Adj Close' if 'Adj Close' in p.columns else 'Close'
            prices[os.path.splitext(f)[0]] = p[col]
        except Exception:
            continue

adapted = PredictionAdapter.adapt_classifier(preds)
trades = PortfolioConstructor.construct_top_k_trades(adapted, prices, k=10)
legacy_port, legacy_cagr, legacy_sharpe, legacy_maxdd, legacy_wr, legacy_avg_ret, legacy_n = ModelAgnosticSimulator.simulate(trades, prices)
new_results = run_pipeline(adapted, prices, k=10, allocator_name='equal_weight')

print('--- Legacy Metrics ---')
print(f'CAGR: {legacy_cagr:.6f}')
print(f'Sharpe: {legacy_sharpe:.6f}')
print(f'Max Drawdown: {legacy_maxdd:.6f}')
print(f'Win Rate: {legacy_wr:.6f}')
print(f'Average Return: {legacy_avg_ret:.6f}')
print(f'Number of Trades: {legacy_n}')

print('\n--- New Pipeline Metrics ---')
print(f"CAGR: {new_results['cagr']:.6f}")
print(f"Sharpe: {new_results['sharpe']:.6f}")
print(f"Max Drawdown: {new_results['max_drawdown']:.6f}")
print(f"Win Rate: {new_results['win_rate']:.6f}")
print(f"Average Return: {new_results['average_return']:.6f}")
print(f"Number of Trades: {new_results['num_trades']}")
