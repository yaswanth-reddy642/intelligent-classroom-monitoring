import os
import json
from typing import Dict, Any

class DatasetValidator:
    def validate_structure(self, root_path: str) -> bool:
        required_dirs = ['train', 'val', 'test', 'annotations']
        for d in required_dirs:
            if not os.path.exists(os.path.join(root_path, d)):
                return False
        return True

    def validate_annotations(self, annotations_path: str) -> bool:
        if not os.path.exists(annotations_path):
            return False
        try:
            with open(annotations_path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return False
                for vid, labels in data.items():
                    if not isinstance(labels, list) or not all(l in [0, 1] for l in labels):
                        return False
            return True
        except Exception:
            return False

    def validate_split(self, split_manifest_path: str) -> bool:
        if not os.path.exists(split_manifest_path):
            return False
        try:
            with open(split_manifest_path, 'r') as f:
                manifest = json.load(f)
                train_vids = set(manifest.get('train', []))
                val_vids = set(manifest.get('val', []))
                test_vids = set(manifest.get('test', []))
                
                # Check overlaps
                if train_vids.intersection(val_vids) or train_vids.intersection(test_vids) or val_vids.intersection(test_vids):
                    return False
            return True
        except Exception:
            return False

    def generate_report(self, root_path: str) -> Dict[str, Any]:
        return {
            'structure_valid': self.validate_structure(root_path),
            'annotations_train_valid': self.validate_annotations(os.path.join(root_path, 'annotations', 'train.json')),
            'annotations_val_valid': self.validate_annotations(os.path.join(root_path, 'annotations', 'val.json')),
            'annotations_test_valid': self.validate_annotations(os.path.join(root_path, 'annotations', 'test.json'))
        }
