import json
import random
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

class SplitValidator:
    def validate_no_video_overlap(self, train_videos: List[str], val_videos: List[str], test_videos: List[str]) -> bool:
        train_set = set(train_videos)
        val_set = set(val_videos)
        test_set = set(test_videos)
        return not (train_set & val_set or train_set & test_set or val_set & test_set)

    def validate_no_sequence_overlap(self, train_seqs: List[str], val_seqs: List[str], test_seqs: List[str]) -> bool:
        # Extracted sequence base IDs shouldn't overlap
        train_set = {s.split('_')[0] for s in train_seqs}
        val_set = {s.split('_')[0] for s in val_seqs}
        test_set = {s.split('_')[0] for s in test_seqs}
        return not (train_set & val_set or train_set & test_set or val_set & test_set)

    def create_split_manifest(self, videos: List[str], ratios: Dict[str, float], seed: int = 42) -> Dict[str, List[str]]:
        random.seed(seed)
        shuffled = list(videos)
        random.shuffle(shuffled)
        
        n = len(shuffled)
        n_train = int(n * ratios.get('train', 0.7))
        n_val = int(n * ratios.get('val', 0.15))
        
        return {
            'train': shuffled[:n_train],
            'val': shuffled[n_train:n_train+n_val],
            'test': shuffled[n_train+n_val:]
        }

    def save_manifest(self, manifest: Dict[str, List[str]], path: str):
        with open(path, 'w') as f:
            json.dump(manifest, f, indent=4)

    def load_manifest(self, path: str) -> Dict[str, List[str]]:
        with open(path, 'r') as f:
            return json.load(f)

    def validate_manifest(self, manifest_path: str) -> ValidationResult:
        errors = []
        try:
            manifest = self.load_manifest(manifest_path)
            train = manifest.get('train', [])
            val = manifest.get('val', [])
            test = manifest.get('test', [])
            if not self.validate_no_video_overlap(train, val, test):
                errors.append("Video overlap detected between splits.")
            return ValidationResult(is_valid=len(errors) == 0, errors=errors)
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[str(e)])
