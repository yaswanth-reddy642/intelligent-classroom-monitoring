import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='results/detection')
    args = parser.parse_args()
    
    models = ['Standard YOLOv11', 'Enhanced Detector']
    
    results = []
    for m in models:
        results.append({
            'Detector': m,
            'Precision': 'N/A',
            'Recall': 'N/A',
            'F1': 'Not yet evaluated',
            'mAP': 'N/A',
            'FPS': 'N/A',
            'Latency': 'N/A'
        })
        
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    out_path = os.path.join(args.output_dir, 'detector_comparison.csv')
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
