# Computer Vision Object Detection

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Computer Vision](https://img.shields.io/badge/Computer%20Vision-Object%20Detection-0EA5E9)](https://github.com/fer-trk/project-ai-computer-vision-objects)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)](https://github.com/fer-trk/project-ai-computer-vision-objects)

Proof of concept for detecting brand logos in images and videos using computer vision.

## Overview

This project explores an end-to-end workflow for logo detection:

- model training and validation;
- image inference with bounding boxes, labels and confidence scores;
- video processing;
- exposure-time analysis by brand;
- result persistence;
- a future API and web interface.

The project is designed with reproducibility, data provenance and evidence-based evaluation in mind.

## Features

- Object detection for brand logos.
- Image prediction and annotated outputs.
- Reproducible training workflow.
- Dataset and artifact validation.
- Manual review of detections.
- Foundations for video analysis and local web deployment.

## Tech Stack

- Python 3.11+
- Ultralytics YOLO
- Jupyter / Google Colab
- FastAPI for the local application layer
- FFmpeg for video-related workflows

## Getting Started

Clone the repository and create a virtual environment:

```powershell
git clone https://github.com/fer-trk/project-ai-computer-vision-objects.git
cd project-ai-computer-vision-objects

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-inference.txt
```

See the documentation in [`docs/`](docs/) for training, evaluation and local application instructions.

## Project Structure

```text
notebooks/   # Exploration, environment checks and training notebooks
scripts/     # Training, inference, evaluation and local application scripts
tests/       # Automated tests
docs/        # Technical documentation and execution guides
```

## Current Status

The project is currently in the proof-of-concept phase.

The training and image-evaluation workflows are prepared for controlled execution. Model performance must be assessed using real evaluation evidence before drawing conclusions about accuracy, generalization or production readiness.

## Data and Models

Datasets, source videos, model weights and generated artifacts are intentionally excluded from version control.

All data used for training or evaluation must have documented provenance, permissions and partitioning.

## Contributing

- Create short, task-focused branches.
- Follow Conventional Commits.
- Add or update tests for relevant logic.
- Do not commit datasets, model weights, generated results, secrets or `.env` files.
- Open a pull request before integrating relevant changes.

## License

The project license and complete dataset licensing information are pending definition before public distribution.
