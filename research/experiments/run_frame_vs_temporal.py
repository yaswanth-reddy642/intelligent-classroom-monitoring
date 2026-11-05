import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='results/comparison')
    args = parser.parse_args()
    
    results = [
        {
            'Model': 'Frame-level (Immediate Alert)',
            'False Positives': 'N/A',
            'Latency (ms)': 'N/A'
        },
        {
            'Model': 'Temporal (Tracking+Association+Verif)',
            'False Positives': 'Not yet evaluated',
            'Latency (ms)': 'N/A'
        }
    ]
    
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    out_path = os.path.join(args.output_dir, 'frame_vs_temporal.csv')
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
