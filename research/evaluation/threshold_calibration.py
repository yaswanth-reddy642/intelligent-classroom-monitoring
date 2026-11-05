import json
import numpy as np
from typing import List, Dict, Any
from sklearn.metrics import f1_score, roc_curve

class ThresholdCalibrator:
    def calibrate_f1(self, val_scores: List[float], val_labels: List[int]) -> float:
        best_f1 = 0
        best_thresh = 0.5
        thresholds = np.linspace(0, 1, 100)
        for t in thresholds:
            preds = (np.array(val_scores) >= t).astype(int)
            f1 = f1_score(val_labels, preds, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = t
        return float(best_thresh)

    def calibrate_fpr(self, val_scores: List[float], val_labels: List[int], target_fpr: float) -> float:
        fpr, _, thresholds = roc_curve(val_labels, val_scores)
        idx = np.where(fpr <= target_fpr)[0]
        if len(idx) == 0:
            return float(thresholds[0])
        return float(thresholds[idx[-1]])

    def calibrate_custom(self, val_scores: List[float], val_labels: List[int], operating_point: float) -> float:
        return operating_point

    def save_calibration(self, threshold: float, metadata: Dict[str, Any], path: str):
        data = {
            'threshold': threshold,
            'metadata': metadata
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
