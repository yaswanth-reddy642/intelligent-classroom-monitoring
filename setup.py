from setuptools import setup, find_packages

setup(
    name="intelligent-classroom-monitoring",
    version="1.0.0",
    description="Intelligent Classroom Monitoring and Anomaly Detection Using YOLOv11",
    author="Intelligent Classroom Monitoring Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "ultralytics>=8.3.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0.1",
        "supervision>=0.25.0",
    ],
    entry_points={
        "console_scripts": [
            "classroom-monitor=ai_pipeline.cli:main",
        ],
    },
)
