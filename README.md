# LoessHazardDetector

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![PyTorch 1.13+](https://img.shields.io/badge/pytorch-1.13%2B-orange.svg)](https://pytorch.org/)

A toolkit for detecting landslides and mining-induced subsidence in the Chinese Loess Plateau. It combines InSAR phase-gradient stacking (PGS) with an improved YOLOv8 model that integrates the AssemFormer attention block.

---

## Overview

The Loess Plateau is one of the most landslide-prone regions in China. Building a complete, up-to-date geohazard inventory across the whole plateau is difficult: field surveys are slow, and manual interpretation of remote sensing images is hard to update at regional scale.
This toolkit is built to speed up that work. It takes a three-band GeoTIFF as input (typically PGS deformation, slope, and DEM) and returns a GIS-ready Shapefile of detected landslides and subsidence zones. Unlike image-based detection tools that operate on PNG tiles without coordinate information, LoessHazardDetector preserves the georeference of the input raster and outputs detection results directly in geographic coordinates. This makes the results ready for further spatial analysis in QGIS, ArcGIS, or Python GIS libraries.

The detector is a customized YOLOv8 in which the C2f block at the P3 neck layer is replaced by **AssemFormer**, a hybrid CNN-Transformer module. The AssemFormer block combines local convolution features with global attention, which helps the detector handle deformation anomalies with unclear boundaries. The model detects two classes of geohazards: **landslides (L)** and **mining-induced subsidence (M)**.

The toolkit supports three tasks:

- **Training** YOLOv5, YOLOv8, YOLO11, and the custom YOLOv8_AssemFormer
- **Validating** a trained model with standard detection metrics
- **Predicting** on large GeoTIFF rasters with sliding-window inference

This codebase is a fork of Ultralytics 8.3.27. The only changes from upstream are the AssemFormer module and its registration. See ultralytics/README.md for details.

---

## Features

- Multi-model support: YOLOv5, YOLOv8, YOLO11, and YOLOv8_AssemFormer
- Two hazard classes: landslides (L) and mining-induced subsidence (M)
- Pretrained initialization for all supported models
- AssemFormer block integrated into the YOLOv8 neck
- Sliding-window inference on arbitrarily large GeoTIFF rasters
- Per-tile percentile stretch for contrast normalization
- Spatial NMS with STRtree acceleration
- Georeferenced Shapefile output (WGS84 or the input raster CRS)
- Unified console output prefixed with [LHD]

---

## Input Data

LoessHazardDetector uses two types of input data for different tasks.

### 1. YOLO-format dataset (for training and validation)

Standard YOLO format: one folder of images and one folder of label files (.txt). Each label file lists bounding boxes in normalized coordinates.
The dataset configuration is a YAML file. An example is provided in data/landslide.yaml. See data/README.md for details.

### 2. GeoTIFF raster (for prediction)

A three-band GeoTIFF representing PGS deformation, slope, and DEM. The raster must contain georeference information (coordinate system, transform). A small sample from Hualong County, Qinghai Province (WGS84) is included at examples/sample.tif for quick testing. For real applications, replace it with a GeoTIFF covering your own study area.

The PGS deformation layer can be generated using existing open-source tools. We recommend the Improved Phase Gradient Stacking (IPGS) implementation from Wuhan University:

- IPGS (primary): https://github.com/whuinsar/IPGS
- IPGS-WHU-InSAR (alternative): https://github.com/gnssguo/IPGS-WHU-InSAR

If you use the PGS/InSAR component in your work, please also cite the
following references:

Fu, L., Zhang, Q., Wang, T., Li, W., Xu, Q., Ge, D., 2022. Detecting slow-moving landslides using InSAR phase-gradient stacking and deep-learning network. Frontiers in Environmental Science 10, 963322.
https://doi.org/10.3389/fenvs.2022.963322

Zhang, D., Zhang, L., Dong, J., Wang, Y., Yang, C., Liao, M., 2024. Improved phase gradient stacking for landslide detection. Landslides 21,
1829-1847. https://doi.org/10.1007/s10346-024-02263-3

---

## Installation

### Requirements

- Python >= 3.8
- PyTorch >= 1.13 (2.0 recommended)
- CUDA (optional, recommended for training and large-scale prediction)

### Steps

1. Clone the repository:

git clone https://github.com/<your-username>/LoessHazardDetector.git
cd LoessHazardDetector

2. Install PyTorch.

For GPU support, install the CUDA build that matches your driver before
installing the rest. For example, with CUDA 11.8:

pip install torch==2.0.0 torchvision==0.15.1 --index-url https://download.pytorch.org/whl/cu118

Check https://pytorch.org/get-started/locally/ for other CUDA versions or
the CPU-only build. If you skip this step, pip will install the CPU-only
version when you run the next command, which works but is slow for training.

3. Install the remaining dependencies:

pip install -r requirements.txt

4. Optional: install as an importable package.

pip install -e .

---

## Quick Start

All tasks are run through main.py. A small example GeoTIFF is included at examples/sample.tif, so you can try the toolkit without preparing your own data first.

1. Predict on a GeoTIFF

python main.py predict

This uses the default weights and the sample raster. Output goes to runs/predict1/result.shp. To use your own data:

python main.py predict --tif /path/to/your.tif

2. Validate a model

python main.py val --weights weights/yolov8_assem.pt --data data/landslide.yaml

Add --plots if you also want confusion matrices and PR curves:

python main.py val --weights weights/yolov8_assem.pt --data data/landslide.yaml --plots

3. Train a model

# Train the custom AssemFormer variant from scratch
python main.py train --model yolov8_assem --epochs 350

# Fine-tune from an existing checkpoint
python main.py train --model yolov8_assem --weights weights/yolov8_assem.pt --epochs 350

# Train official YOLOv8 from pretrained weights
python main.py train --model yolov8 --pretrained --epochs 350

Results are written to runs/train, runs/train2, and so on.

---

## Configuration

LoessHazardDetector reads its defaults from configs/default.yaml. Values are applied in this order, from lowest to highest priority:

1. configs/default.yaml
2. A user config passed via --config <path>
3. Command-line arguments

This means you can keep a project-level YAML for your usual settings, and override just one or two values on the command line when needed.

### Using the default configuration

Just run the task without --config:

python main.py train --model yolov8_assem

### Overriding a single value

python main.py train --model yolov8_assem --epochs 350 --batch 4

### Creating a custom configuration

Copy the default config and edit the values you need:

cp configs/default.yaml configs/my_exp.yaml
# edit configs/my_exp.yaml

Then run with --config:

python main.py train --config configs/my_exp.yaml

### Combining a custom config with CLI overrides

python main.py train --config configs/my_exp.yaml --lr0 0.0005

### Provided configuration files

We provide several ready-to-use configuration files in configs/:

| File                     | Purpose                                                       |
|--------------------------|---------------------------------------------------------------|
| configs/default.yaml     | Default settings for all tasks                                |
| configs/yolov8n.yaml     | Train YOLOv8n for baseline comparison                         |
| configs/yolo11n.yaml     | Train YOLO11n for baseline comparison                         |
| configs/assemformer.yaml | Train YOLOv8_AssemFormer (the main model of this project)     |

To compare multiple models, run training with each config separately:

python main.py train --config configs/yolov8n.yaml
python main.py train --config configs/yolo11n.yaml
python main.py train --config configs/assemformer.yaml

Then compare the results in runs/train, runs/train2, runs/train3.

See configs/README.md for the full list of options.

---

## Model Weights

Pretrained and fine-tuned weights are stored in weights/.

| File                      | Source                                  | Usage                                      |
|---------------------------|-----------------------------------------|--------------------------------------------|
| weights/yolov8n.pt        | Official Ultralytics YOLOv8n            | --model yolov8 --pretrained                |
| weights/yolov8s.pt        | Official Ultralytics YOLOv8s (optional) | --model yolov8 --pretrained                |
| weights/yolo11n.pt        | Official Ultralytics YOLO11n            | --model yolo11 --pretrained                |
| weights/yolov8_assem.pt   | Trained on Loess Plateau dataset        | Default weight for prediction and fine-tuning |

### Using pretrained weights

For official models, pass --pretrained:

python main.py train --model yolov8 --pretrained

For the custom AssemFormer model, --pretrained loads
weights/yolov8_assem.pt automatically:

python main.py train --model yolov8_assem --pretrained

### Fine-tuning from a checkpoint

python main.py train --model yolov8_assem --weights weights/yolov8_assem.pt --epochs 100

### Using weights for prediction

python main.py predict --weights weights/yolov8_assem.pt

See weights/README.md for details.

---

## Project Structure

LoessHazardDetector/
├── ultralytics/     # Ultralytics 8.3.27 fork with AssemFormer
├── Framework/       # Task wrappers and the detection engine
├── weights/         # Pretrained and fine-tuned model weights
├── data/            # Dataset configuration and examples
├── configs/         # YAML configuration files
├── examples/        # Sample GeoTIFF from Hualong County, Qinghai
├── runs/            # Output directory for all tasks
├── main.py          # Command-line entry point
├── requirements.txt
├── pyproject.toml
└── README.md

Each folder has its own README with details:

- ultralytics/README.md — what was changed from upstream
- Framework/README.md — what each Python module does
- weights/README.md — what weights are included
- data/README.md — how to prepare your dataset
- configs/README.md — full parameter reference

---

## Command-Line Overview

The general form is:

python main.py <task> [options]

Where <task> is train, val, or predict.

Common arguments:

| Argument   | Default                   | Description                                    |
|------------|---------------------------|------------------------------------------------|
| --config   | configs/default.yaml      | Path to a YAML configuration file              |
| --model    | yolov8_assem              | Model name (see Framework/README.md)           |
| --weights  | weights/yolov8_assem.pt   | Path to a weight file                          |
| --data     | data/landslide.yaml       | Dataset YAML path                              |
| --device   | auto                      | cuda:0, cpu, or leave empty for auto-detect    |

Task-specific arguments:

Run "python main.py <task> --help" for the full list.

| Task    | Key arguments                                              |
|---------|------------------------------------------------------------|
| train   | --epochs, --lr0, --batch, --workers, --pretrained          |
| val     | --split, --plots, --save-json                              |
| predict | --tif, --out, --tile, --stride, --conf, --merge-iou        |

For a complete parameter reference, see configs/README.md.

---

## Output

All results are written under runs/:

runs/
├── train/          # first training run
├── train2/         # second training run
├── val/            # first validation run
├── val2/
├── predict1/       # first prediction run
└── predict2/

Training and validation directories follow the Ultralytics convention: the
first run uses the plain name (train, val), and later runs get a numeric
suffix. Prediction runs are numbered from 1 (predict1, predict2, ...).

Shapefile fields:

| Field | Type  | Description                                    |
|-------|-------|------------------------------------------------|
| cls   | int   | Class index (0 = landslide, 1 = subsidence)    |
| conf  | float | Detection confidence                           |
| class | str   | Class label (L = landslide, M = subsidence)    |

The Shapefile preserves the coordinate system of the input GeoTIFF, so it
can be loaded directly into QGIS, ArcGIS, or Python GIS libraries for further
analysis.

---

## Citation

If you use this software in your research, please cite:

@software{loesshazarddetector2025,
  title  = {LoessHazardDetector: A toolkit for automatic geohazard detection in the Chinese Loess Plateau},
  author = {<authors to be added>},
  year   = {2025},
  url    = {https://github.com/<your-username>/LoessHazardDetector}
}

This project builds on Ultralytics YOLO. Please cite it as well:

@software{ultralytics2023yolo,
  title  = {Ultralytics YOLOv8},
  author = {Jocher, Glenn and Chaurasia, Ayush and Qiu, Jing},
  year   = {2023},
  url    = {https://github.com/ultralytics/ultralytics}
}

The PGS deformation layer should be generated using the IPGS tools from
Wuhan University. Please cite:

@article{fu2022detecting,
  title   = {Detecting slow-moving landslides using InSAR phase-gradient stacking and deep-learning network},
  author  = {Fu, Lv and Zhang, Qi and Wang, Teng and Li, Weile and Xu, Qiang and Ge, Daqing},
  journal = {Frontiers in Environmental Science},
  volume  = {10},
  pages   = {963322},
  year    = {2022},
  doi     = {10.3389/fenvs.2022.963322}
}

@article{zhang2024improved,
  title   = {Improved phase gradient stacking for landslide detection},
  author  = {Zhang, Dongxiao and Zhang, Lu and Dong, Jie and Wang, Yian and Yang, Chengsheng and Liao, Mingsheng},
  journal = {Landslides},
  volume  = {21},
  pages   = {1829--1847},
  year    = {2024},
  doi     = {10.1007/s10346-024-02263-3}
}

---

## License

This project is licensed under the GNU Affero General Public License v3.0
(AGPL-3.0), inherited from Ultralytics. See LICENSE for the full text.

---

## Acknowledgements

- Ultralytics (https://github.com/ultralytics/ultralytics) for the YOLO framework
- Wuhan University InSAR team (https://github.com/whuinsar) for the IPGS code
- Alaska Satellite Facility (https://asf.alaska.edu/) for HyP3 interferometric products
- ESA for Sentinel-1 SAR data
- JAXA for the AW3D30 DEM
