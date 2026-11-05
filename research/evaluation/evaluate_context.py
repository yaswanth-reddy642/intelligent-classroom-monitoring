import pandas as pd
from typing import List, Dict

class ContextEvaluator:
    def compare_with_without_context(self, predictions_no_ctx: List[int], predictions_ctx: List[int], ground_truth: List[Dict]) -> Dict[str, Dict[str, float]]:
        """
        ground_truth: List of dicts with 'label' and 'context' (e.g. 'LECTURE', 'EXAM')
        """
        results = {}
        contexts = set(gt['context'] for gt in ground_truth)
        
        for ctx in contexts:
            idx = [i for i, gt in enumerate(ground_truth) if gt['context'] == ctx]
            y_true = [ground_truth[i]['label'] for i in idx]
            y_no_ctx = [predictions_no_ctx[i] for i in idx]
            y_ctx = [predictions_ctx[i] for i in idx]
            
            fp_no_ctx = sum(1 for yt, yp in zip(y_true, y_no_ctx) if yt == 0 and yp == 1)
            fp_ctx = sum(1 for yt, yp in zip(y_true, y_ctx) if yt == 0 and yp == 1)
            
            reduction = (fp_no_ctx - fp_ctx) / max(fp_no_ctx, 1)
            
            results[ctx] = {
                'fp_no_context': fp_no_ctx,
                'fp_context': fp_ctx,
                'fp_reduction_rate': reduction
            }
            
        return results

    def save_results(self, results: Dict[str, Dict[str, float]], path: str):
        df = pd.DataFrame.from_dict(results, orient='index')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'context'}, inplace=True)
        df.to_csv(path, index=False)
