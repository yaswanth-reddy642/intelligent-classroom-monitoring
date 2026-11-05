import os
import json
import torch
from torch.utils.data import Dataset
from PIL import Image
import glob
from typing import Optional, Callable, Dict, Any, Tuple, List

class VADDataset(Dataset):
    """
    Video Anomaly Detection dataset.
    Loads sequences of frames for training temporal models.
    """
    def __init__(self, sequences: List[Dict[str, Any]], transform: Optional[Callable] = None):
        """
        Args:
            sequences: List of dictionaries containing 'frames' (list of paths) and 'label' (int)
            transform: torchvision transforms
        """
        self.sequences = sequences
        self.transform = transform
        
    def __len__(self) -> int:
        return len(self.sequences)
        
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, Dict[str, Any]]:
        seq = self.sequences[idx]
        frame_paths = seq['frames']
        label = seq['label']
        
        frames = []
        for path in frame_paths:
            img = Image.open(path).convert('RGB')
            if self.transform:
                img = self.transform(img)
            frames.append(img)
            
        # Stack into (C, T, H, W) or (T, C, H, W) depending on transform
        if len(frames) > 0 and isinstance(frames[0], torch.Tensor):
            frames_tensor = torch.stack(frames, dim=0)
        else:
            frames_tensor = frames
            
        metadata = {
            'start_frame': seq.get('start_frame', -1),
            'video_id': seq.get('video_id', 'unknown')
        }
        
        return frames_tensor, label, metadata
        
    @classmethod
    def from_directory(cls, root: str, split: str = 'train', seq_length: int = 16, 
                       stride: int = 8, transform: Optional[Callable] = None) -> 'VADDataset':
        """
        Create dataset from directory structure.
        Expects: root/split/video_id/*.jpg
        And annotations in: root/annotations/{split}.json
        """
        split_dir = os.path.join(root, split)
        annotations_path = os.path.join(root, 'annotations', f"{split}.json")
        
        labels_map = {}
        if os.path.exists(annotations_path):
            with open(annotations_path, 'r') as f:
                labels_map = json.load(f)
                
        sequences = []
        if os.path.exists(split_dir):
            videos = [d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))]
            for video in videos:
                vid_dir = os.path.join(split_dir, video)
                frames = sorted(glob.glob(os.path.join(vid_dir, '*.jpg')) + glob.glob(os.path.join(vid_dir, '*.png')))
                
                # Default label 0 if not specified
                vid_labels = labels_map.get(video, [0] * len(frames))
                
                for i in range(0, len(frames) - seq_length + 1, stride):
                    seq_frames = frames[i:i+seq_length]
                    seq_labels = vid_labels[i:i+seq_length]
                    # If any frame is anomalous (1), sequence is anomalous
                    seq_label = 1 if any(l == 1 for l in seq_labels) else 0
                    
                    sequences.append({
                        'frames': seq_frames,
                        'label': seq_label,
                        'start_frame': i,
                        'video_id': video
                    })
                    
        return cls(sequences, transform=transform)
