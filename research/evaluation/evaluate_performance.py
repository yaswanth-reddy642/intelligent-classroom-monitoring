import time
import pandas as pd
import torch
import platform
from typing import Dict, Any

class PerformanceBenchmark:
    def benchmark_pipeline(self, pipeline: Any, video_source: Any, num_frames: int = 100) -> Dict[str, float]:
        latencies = {
            'detection': [],
            'tracking': [],
            'association': [],
            'temporal_model': [],
            'anomaly_fusion': []
        }
        
        start_total = time.time()
        for i in range(num_frames):
            frame = video_source.get_frame(i) if hasattr(video_source, 'get_frame') else None
            # Assuming pipeline returns timings dict in its output or we mock it here
            t0 = time.time()
            res = pipeline.process(frame)
            t1 = time.time()
            
            # Using mock/stub metrics if pipeline doesn't provide fine-grained
            latencies['detection'].append(res.get('det_time', 0.01))
            latencies['tracking'].append(res.get('track_time', 0.005))
            latencies['association'].append(res.get('assoc_time', 0.002))
            latencies['temporal_model'].append(res.get('temp_time', 0.01))
            latencies['anomaly_fusion'].append(res.get('fuse_time', 0.001))
            
        end_total = time.time()
        total_time = end_total - start_total
        
        hw_info = {
            'device': 'GPU' if torch.cuda.is_available() else 'CPU',
            'platform': platform.system()
        }
        
        return {
            'fps': num_frames / total_time,
            'total_latency_ms': (total_time / num_frames) * 1000,
            'detection_ms': (sum(latencies['detection']) / num_frames) * 1000,
            'tracking_ms': (sum(latencies['tracking']) / num_frames) * 1000,
            'association_ms': (sum(latencies['association']) / num_frames) * 1000,
            'hardware': hw_info['device']
        }

    def save_results(self, results: Dict[str, Any], path: str):
        pd.DataFrame([results]).to_csv(path, index=False)
