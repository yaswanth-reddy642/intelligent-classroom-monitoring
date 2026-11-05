"""Video input module for classroom monitoring."""
from ai_pipeline.video.video_source import (
    VideoSource,
    FileVideoSource,
    WebcamVideoSource,
    RTSPVideoSource,
    create_video_source,
)

__all__ = [
    'VideoSource',
    'FileVideoSource', 
    'WebcamVideoSource',
    'RTSPVideoSource',
    'create_video_source',
]
