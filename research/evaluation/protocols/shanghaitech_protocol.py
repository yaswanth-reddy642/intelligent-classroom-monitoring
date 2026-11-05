def evaluate_shanghaitech(predictions, ground_truth):
    """
    Standard protocol for ShanghaiTech dataset evaluation.
    Frame-level AUC.
    """
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(ground_truth, predictions)
