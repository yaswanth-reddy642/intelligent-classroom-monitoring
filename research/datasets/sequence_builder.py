import cv2
import os
import glob
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SequenceInfo:
    frames: List[str]
    start_idx: int
    end_idx: int
    start_time: float
    end_time: float

class SequenceBuilder:
    """
    Builds temporal sequences from videos or frame directories.
    """
    def __init__(self, fps: int = 30, seq_length: int = 16, stride: int = 8):
        self.fps = fps
        self.seq_length = seq_length
        self.stride = stride

    def build_from_directory(self, dir_path: str, ext: str = '*.jpg') -> List[SequenceInfo]:
        frames = sorted(glob.glob(os.path.join(dir_path, ext)))
        sequences = []
        for i in range(0, max(1, len(frames) - self.seq_length + 1), self.stride):
            seq_frames = frames[i:i+self.seq_length]
            if not seq_frames:
                break
            start_time = i / self.fps
            end_time = (i + len(seq_frames)) / self.fps
            sequences.append(SequenceInfo(
                frames=seq_frames,
                start_idx=i,
                end_idx=i + len(seq_frames) - 1,
                start_time=start_time,
                end_time=end_time
            ))
        return sequences

    def build_from_video(self, video_path: str, output_dir: str) -> List[SequenceInfo]:
        os.makedirs(output_dir, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or self.fps
        
        frame_idx = 0
        saved_frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_path = os.path.join(output_dir, f"frame_{frame_idx:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            saved_frames.append(frame_path)
            frame_idx += 1
            
        cap.release()
        
        sequences = []
        for i in range(0, max(1, len(saved_frames) - self.seq_length + 1), self.stride):
            seq_frames = saved_frames[i:i+self.seq_length]
            if not seq_frames:
                break
            sequences.append(SequenceInfo(
                frames=seq_frames,
                start_idx=i,
                end_idx=i + len(seq_frames) - 1,
                start_time=i / fps,
                end_time=(i + len(seq_frames)) / fps
            ))
        return sequences
