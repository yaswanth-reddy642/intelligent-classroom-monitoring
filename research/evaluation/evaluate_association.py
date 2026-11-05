import json
import pandas as pd
from typing import Dict, List
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

class AssociationEvaluator:
    def evaluate(self, predictions: List[Dict], ground_truth_annotations: List[Dict]) -> Dict[str, float]:
        """
        predictions: [{'student_id': X, 'phone_id': Y, 'is_associated': 1/0}, ...]
        ground_truth_annotations: [{'student_id': X, 'phone_id': Y, 'is_associated': 1/0, 'condition': '...'}, ...]
        """
        y_true = []
        y_pred = []
        
        pred_map = {(p['student_id'], p['phone_id']): p['is_associated'] for p in predictions}
        
        for gt in ground_truth_annotations:
            key = (gt['student_id'], gt['phone_id'])
            y_true.append(gt['is_associated'])
            y_pred.append(pred_map.get(key, 0)) # Default to 0 if not predicted
            
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
        accuracy = accuracy_score(y_true, y_pred)
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'accuracy': float(accuracy)
        }

    def save_results(self, results: Dict[str, float], path: str):
        pd.DataFrame([results]).to_csv(path, index=False)
