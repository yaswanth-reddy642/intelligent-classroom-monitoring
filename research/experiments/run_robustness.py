import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='results/robustness')
    args = parser.parse_args()
    
    conditions = [
        "normal", "occlusion", "small phones", "crowded", 
        "low-light", "motion blur", "camera angles", "missed detections"
    ]
    
    results = []
    for cond in conditions:
        results.append({
            'Condition': cond,
            'F1-Score': 'Not yet evaluated',
            'Accuracy': 'N/A'
        })
        
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    out_path = os.path.join(args.output_dir, 'robustness_results.csv')
    df.to_csv(out_path, index=False)
    print(f"Saved robustness results to {out_path}")

if __name__ == '__main__':
    main()
