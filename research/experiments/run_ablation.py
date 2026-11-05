import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='results/ablation')
    args = parser.parse_args()
    
    configs = [
        "YOLOv11 only",
        "+ tracking",
        "+ association",
        "+ temporal verification",
        "Full context-aware",
        "CNN-LSTM",
        "Temporal Transformer",
        "Full proposed system"
    ]
    
    results = []
    for cfg in configs:
        results.append({
            'Configuration': cfg,
            'Precision': 'N/A',
            'Recall': 'N/A',
            'F1-Score': 'Not yet evaluated',
            'Latency (ms)': 'N/A'
        })
        
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    out_path = os.path.join(args.output_dir, 'ablation_results.csv')
    df.to_csv(out_path, index=False)
    print(f"Saved ablation results to {out_path}")

if __name__ == '__main__':
    main()
