# configs/

This folder contains YAML configuration files for LoessHazardDetector.

Instead of passing every parameter on the command line, you can put your
settings into a YAML file and load it with --config. This is especially
useful when you want to keep a fixed set of parameters for a project, or
when you want to run the same experiment multiple times with identical
settings.

---

## How configuration works

LoessHazardDetector reads parameters from three sources. When the same
parameter is set in more than one place, the source with higher priority
wins:

1. configs/default.yaml       (lowest priority, always loaded)
2. A user config passed via --config <path>
3. Command-line arguments     (highest priority)

In short: command line > custom config > default config.

This design lets you keep a project-level YAML for your usual settings, and
override just one or two values on the command line when needed.

---

## Provided configuration files

| File                       | Purpose                                                    |
|----------------------------|------------------------------------------------------------|
| configs/default.yaml       | Default settings for all tasks                             |
| configs/yolov8n.yaml       | Train YOLOv8n for baseline comparison                      |
| configs/yolo11n.yaml       | Train YOLO11n for baseline comparison                      |
| configs/assemformer.yaml   | Train YOLOv8_AssemFormer (the main model of this project)  |

To compare multiple models, run training with each config separately:

python main.py train --config configs/yolov8n.yaml
python main.py train --config configs/yolo11n.yaml
python main.py train --config configs/assemformer.yaml

Each run writes to its own directory under runs/, so you can compare the
results side by side.

---

## Three ways to use configurations

### 1. Use defaults without changing anything

Just run the task without --config:

python main.py train --model yolov8_assem

Everything is taken from configs/default.yaml.

### 2. Edit configs/default.yaml directly

If you want your changes to apply to every future run, edit the default
file. For example, change epochs from 350 to 100:

# in configs/default.yaml
train:
  epochs: 100

Then run as usual:

python main.py train --model yolov8_assem

### 3. Create a new config file

If you want to keep the default untouched, copy it and edit the copy:

cp configs/default.yaml configs/my_exp.yaml
# edit configs/my_exp.yaml as needed
python main.py train --config configs/my_exp.yaml

### 4. Override one or two values on the command line

Even with a config file, you can still override individual values:

python main.py train --config configs/my_exp.yaml --lr0 0.0005 --batch 4

This is useful for quick experiments without editing any file.

---

## Parameter reference

The default configuration is organized into six sections: model, data,
train, val, predict, and device.

### model

| Parameter   | Type   | Default                    | Description                                       |
|-------------|--------|----------------------------|---------------------------------------------------|
| name        | string | yolov8_assem               | Model name (see Framework/README.md)              |
| weights     | string | weights/yolov8_assem.pt    | Path to a weight file used for training/predict   |
| pretrained  | bool   | false                      | Load the model's default pretrained weight        |

### data

| Parameter   | Type   | Default                 | Description                       |
|-------------|--------|-------------------------|-----------------------------------|
| yaml        | string | data/landslide.yaml     | Dataset YAML path for train/val   |

### train

| Parameter   | Type   | Default | Description                          |
|-------------|--------|---------|--------------------------------------|
| epochs      | int    | 350     | Number of training epochs            |
| lr0         | float  | 0.001   | Initial learning rate                |
| batch       | int    | 8       | Batch size                           |
| workers     | int    | 8       | DataLoader workers                   |
| imgsz       | int    | 512     | Training image size                  |

### val

| Parameter   | Type   | Default | Description                                     |
|-------------|--------|---------|-------------------------------------------------|
| split       | string | val     | Dataset split to evaluate (val or test)         |
| plots       | bool   | false   | Generate validation plots (see note below)      |
| save_json   | bool   | false   | Export validation predictions as COCO JSON      |

Note on plots:

- plots: false (default)
  Only the standard metrics are printed to the console and saved to
  runs/val/results.csv. No images are generated.

- plots: true
  In addition to the metrics, Ultralytics generates several diagnostic
  images in runs/val/, including:
    confusion_matrix.png     - per-class confusion matrix
    PR_curve.png             - precision-recall curve
    P_curve.png, R_curve.png, F1_curve.png
    val_batch0_labels.jpg    - ground truth samples
    val_batch0_pred.jpg      - prediction samples

  Use plots: true when you want to inspect model behavior visually, for
  example when preparing figures for a paper.

### predict

| Parameter     | Type        | Default         | Description                                                |
|---------------|-------------|-----------------|------------------------------------------------------------|
| tif           | string      | examples/sample.tif | Input GeoTIFF path                                     |
| out           | string/null | null            | Output Shapefile. If null, auto-numbered runs/predictN/    |
| tile          | int         | 512             | Sliding-window tile size                                   |
| stride        | int         | 480             | Sliding-window stride                                      |
| edge_policy   | string      | include_last    | Edge handling: include_last, skip_small_tail, single_tile  |
| band_order    | list        | [1, 2, 3]       | Band indices for R, G, B (1-based)                         |
| lower         | float       | 5.0             | Lower percentile for contrast stretch                      |
| upper         | float       | 95.0            | Upper percentile for contrast stretch                      |
| gamma         | float/null  | null            | Optional gamma correction (null = no correction)           |
| imgsz         | int         | 512             | Inference image size                                       |
| conf          | float       | 0.25            | Confidence threshold                                       |
| merge_iou     | float       | 0.5             | IoU threshold for spatial NMS                              |

A few of these deserve a short explanation:

- band_order
  Which bands of the GeoTIFF to use as R, G, B. The default [1, 2, 3] means
  band 1 = PGS deformation, band 2 = slope, band 3 = DEM. If your GeoTIFF
  has a different band order, change this list accordingly.

- lower / upper
  Each tile is stretched to 0-255 using these percentiles. The default
  5th-95th percentile reduces the effect of extreme values. Lower values
  (e.g. 2 and 98) give more contrast but may saturate more pixels.

- edge_policy
  How to handle the last tile on the right and bottom edges of a large
  raster. include_last always covers the full extent; skip_small_tail skips
  the last tile if the leftover is small; single_tile is for debugging only.

- merge_iou
  After per-tile detection, boxes that overlap across tiles are merged using
  spatial NMS. merge_iou controls how aggressively overlapping boxes of the
  same class are suppressed. Higher values keep more boxes.

### device

| Parameter   | Type        | Default | Description                                        |
|-------------|-------------|---------|----------------------------------------------------|
| device      | string/null | null    | null = auto-detect, or "cuda:0", "cpu", etc.       |

---

## Example: switching between models

To train YOLOv8n as a baseline:

python main.py train --config configs/yolov8n.yaml

To train YOLOv8_AssemFormer with the same settings but a different learning
rate:

python main.py train --config configs/assemformer.yaml --lr0 0.0005

To validate the trained AssemFormer model:

python main.py val --weights weights/yolov8_assem.pt --data data/landslide.yaml --plots

To run prediction with the default settings:

python main.py predict

To predict on a custom GeoTIFF and change the confidence threshold:

python main.py predict --tif /path/to/your.tif --conf 0.3