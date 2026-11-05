def evaluate_ucsd(predictions, ground_truth):
    """
    Standard protocol for UCSD Ped2 dataset evaluation.
    Frame-level AUC.
    """
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(ground_truth, predictions)
