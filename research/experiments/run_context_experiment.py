import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='results/context')
    args = parser.parse_args()
    
    contexts = ['LECTURE', 'EXAM', 'AUTHORIZED', 'BREAK']
    
    results = []
    for ctx in contexts:
        results.append({
            'Context': ctx,
            'FP Without Context': 'N/A',
            'FP With Context': 'Not yet evaluated',
            'Reduction Rate': 'N/A'
        })
        
    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.DataFrame(results)
    out_path = os.path.join(args.output_dir, 'context_experiment.csv')
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
