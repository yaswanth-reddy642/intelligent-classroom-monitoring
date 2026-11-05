import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
from typing import Dict, List, Any

class VADEvaluator:
    def evaluate(self, predictions: List[float], ground_truth: List[int], threshold: float = 0.5) -> Dict[str, float]:
        preds_binary = (np.array(predictions) >= threshold).astype(int)
        gt = np.array(ground_truth)
        
        precision, recall, f1, _ = precision_recall_fscore_support(gt, preds_binary, average='binary', zero_division=0)
        accuracy = accuracy_score(gt, preds_binary)
        
        roc_auc = roc_auc_score(gt, predictions) if len(np.unique(gt)) > 1 else float('nan')
        pr_auc = average_precision_score(gt, predictions) if len(np.unique(gt)) > 1 else float('nan')
        
        tn, fp, fn, tp = confusion_matrix(gt, preds_binary, labels=[0, 1]).ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'accuracy': float(accuracy),
            'roc_auc': float(roc_auc),
            'pr_auc': float(pr_auc),
            'fpr': float(fpr),
            'fnr': float(fnr)
        }

    def save_results(self, results: Dict[str, float], path: str):
        df = pd.DataFrame([results])
        df.to_csv(path, index=False)

    def generate_roc_curve(self, predictions: List[float], ground_truth: List[int], save_path: str):
        from sklearn.metrics import roc_curve
        fpr, tpr, _ = roc_curve(ground_truth, predictions)
        plt.figure()
        plt.plot(fpr, tpr)
        plt.xlabel('FPR')
        plt.ylabel('TPR')
        plt.title('ROC Curve')
        plt.savefig(save_path)
        plt.close()

    def generate_pr_curve(self, predictions: List[float], ground_truth: List[int], save_path: str):
        from sklearn.metrics import precision_recall_curve
        prec, rec, _ = precision_recall_curve(ground_truth, predictions)
        plt.figure()
        plt.plot(rec, prec)
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('PR Curve')
        plt.savefig(save_path)
        plt.close()
