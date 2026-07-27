import pandas as pd
import numpy as np
import json

def compute_ndcg_v2(y_true, total_ones, k):
    y_true = np.asarray(y_true)[:k]
    dcg = np.sum(y_true / np.log2(np.arange(2, len(y_true) + 2)))
    
    ideal_ones = min(total_ones, k)
    if ideal_ones == 0:
        return 0.0
    ideal_y = np.ones(ideal_ones)
    idcg = np.sum(ideal_y / np.log2(np.arange(2, len(ideal_y) + 2)))
    return dcg / idcg

def mrr(y_true):
    y_true = np.asarray(y_true)
    ones = np.where(y_true == 1)[0]
    if len(ones) == 0:
        return 0.0
    return 1.0 / (ones[0] + 1)

def main():
    preds = pd.read_csv('test_predictions.csv')
    preds['Date'] = pd.to_datetime(preds['Date'])
    
    results = []
    
    for date, group in preds.groupby('Date'):
        group = group.sort_values('xg_proba', ascending=False)
        y_true = group['target'].values
        total_ones = np.sum(y_true)
        n = len(y_true)
        
        # P@K
        p5 = np.mean(y_true[:5]) if n >= 5 else np.mean(y_true)
        p10 = np.mean(y_true[:10]) if n >= 10 else np.mean(y_true)
        p20 = np.mean(y_true[:20]) if n >= 20 else np.mean(y_true)
        
        # NDCG@K
        ndcg5 = compute_ndcg_v2(y_true, total_ones, 5)
        ndcg10 = compute_ndcg_v2(y_true, total_ones, 10)
        ndcg20 = compute_ndcg_v2(y_true, total_ones, 20)
        
        # MRR
        day_mrr = mrr(y_true)
        
        # Lift
        base_rate = np.mean(y_true)
        decile_n = max(1, int(0.1 * n))
        quintile_n = max(1, int(0.2 * n))
        
        decile_rate = np.mean(y_true[:decile_n])
        quintile_rate = np.mean(y_true[:quintile_n])
        
        decile_lift = decile_rate / base_rate if base_rate > 0 else 1.0
        quintile_lift = quintile_rate / base_rate if base_rate > 0 else 1.0
        
        # Confidence Diagnostics
        prob = group['xg_proba']
        count_75 = np.sum(prob > 0.75)
        mean_prob = prob.mean()
        std_prob = prob.std()
        max_prob = prob.max()
        
        results.append({
            'Date': date.strftime('%Y-%m-%d'),
            'P@5': p5, 'P@10': p10, 'P@20': p20,
            'NDCG@5': ndcg5, 'NDCG@10': ndcg10, 'NDCG@20': ndcg20,
            'MRR': day_mrr,
            'Decile_Lift': decile_lift,
            'Quintile_Lift': quintile_lift,
            'Base_Rate': base_rate,
            'Count_75': int(count_75),
            'Mean_Prob': mean_prob,
            'Std_Prob': std_prob,
            'Max_Prob': max_prob,
            'N_Stocks': n
        })
    
    df = pd.DataFrame(results)
    
    high_conf_days = df.sort_values('Count_75', ascending=False).head(5)
    
    summary = {
        'Daily Ranking (Averages)': {
            'Precision@5': df['P@5'].mean(),
            'Precision@10': df['P@10'].mean(),
            'Precision@20': df['P@20'].mean(),
            'NDCG@5': df['NDCG@5'].mean(),
            'NDCG@10': df['NDCG@10'].mean(),
            'NDCG@20': df['NDCG@20'].mean(),
            'MRR': df['MRR'].mean()
        },
        'Daily Lift (Averages)': {
            'Top Decile Lift': df['Decile_Lift'].mean(),
            'Top Quintile Lift': df['Quintile_Lift'].mean()
        },
        'Confidence Diagnostics': {
            'Avg count > 0.75 per day': df['Count_75'].mean(),
            'Avg Mean Prob': df['Mean_Prob'].mean(),
            'Avg Std Prob': df['Std_Prob'].mean(),
            'Avg Max Prob': df['Max_Prob'].mean()
        },
        'High Concentration Days': high_conf_days[['Date', 'Count_75', 'Max_Prob', 'P@10']].to_dict('records')
    }
    
    with open('eval_results.json', 'w') as f:
        json.dump(summary, f, indent=2)

if __name__ == '__main__':
    main()
