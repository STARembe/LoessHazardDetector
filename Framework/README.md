# Framework/

The Framework/ package wraps Ultralytics into a task-oriented interface. Each module has a single responsibility, and any of them can be imported directly in Python if you want to use LoessHazardDetector as a library instead of through the command line.

---

## Contents

Framework/
├── logger.py           # shared logger with [LHD] prefix
├── config.py           # YAML + CLI configuration loader
├── model_registry.py   # model name -> yaml + default weight
├── train.py            # training wrapper
├── validate.py         # validation wrapper
├── predict.py          # prediction entry point
└── detector.py         # core sliding-window detection engine

---

## logger.py

A single shared logger for the whole toolkit. All output goes through this module, so every line is prefixed with [LHD].

Main API:

from Framework.logger import get_logger, section, subsection
log = get_logger()
log.info("Loading model: %s", path)
section("LoessHazardDetector :: Training")
subsection("Hyperparameters")

Why it exists: to keep console output consistent and easy to filter. If you ever want to write the log to a file, or change the verbosity, you only need to edit this file.

---

## config.py

Loads configuration from three sources, in this order of priority:

1. configs/default.yaml      (always loaded)
2. A user config via --config
3. Command-line arguments

The merge logic lives in load_config(). Command-line arguments use argparse.SUPPRESS as their default, so only values explicitly typed by the
user appear in the merged result. This is what makes "command line overrides config file" work correctly.

Main API:

from Framework.config import load_config
cfg = load_config(args, task="predict")
print(cfg["predict"]["conf"])

The result is a nested dict with sections: model, data, train, val, predict, and a top-level device field.

---

## model_registry.py

Maps a model name to its YAML config and its default pretrained weight.
This is the single place where supported architectures are listed.

Current entries:

| Name          | YAML                                                | Default weight              |
|---------------|-----------------------------------------------------|-----------------------------|
| yolov5        | cfg/models/v5/yolov5.yaml                           | None                        |
| yolov8        | cfg/models/v8/yolov8.yaml                           | weights/yolov8n.pt          |
| yolo11        | cfg/models/11/yolo11.yaml                           | weights/yolo11n.pt          |
| yolov8_assem  | cfg/models/v8/yolov8-assemformer.yaml               | weights/yolov8_assem.pt     |

Main API:

from Framework.model_registry import get_model_config, list_models
cfg = get_model_config("yolov8_assem")
print(cfg["yaml"], cfg["default_weight"])

To add a new architecture, append an entry to MODEL_REGISTRY. No other file needs to change.

---

## train.py

Wraps YOLO.train() with the toolkit's logging and configuration conventions.

What it does:
- Reads the model's YAML and default weight from model_registry
- Initializes the model according to the following priority:
    1. weights provided by the user  -> YOLO(yaml).load(weights)
    2. --pretrained                   -> YOLO(default_weight)
    3. neither                        -> YOLO(yaml), random init
- Calls model.train() with parameters from the config
- Writes outputs to runs/train, runs/train2, ...

Key parameters passed through to Ultralytics:
data, epochs, lr0, imgsz, batch, workers, device

Main API:

from Framework.train import train
train(
    model_name="yolov8_assem",
    data="data/landslide.yaml",
    weights="weights/yolov8_assem.pt",
    epochs=100,
)

---

## validate.py

Wraps YOLO.val() with the same conventions.

What it does:
- Loads the model from a weight file
- Runs validation on the chosen split (val or test)
- Writes metrics, and optionally plots, to runs/val, runs/val2, ...

Key parameters passed through to Ultralytics:
data, split, plots, save_json, device

The plots flag controls whether diagnostic images are generated. When it is false, only the numeric metrics are printed and saved to results.csv. When it is true, Ultralytics also writes confusion matrices, PR curves, and sample prediction images to the run directory.

Main API:

from Framework.validate import validate
validate(
    weights="weights/yolov8_assem.pt",
    data="data/landslide.yaml",
    split="val",
    plots=True,
)

---

## predict.py

Entry point for the predict task. It handles output path resolution, then hands the actual work to detector.py.

What it does:
- If no --out is given, calls next_run_dir("runs", "predict") to generate
  a unique directory such as runs/predict1, runs/predict2, ...
- Prints a summary of the parameters being used
- Calls detect_to_shp() in detector.py
- Does not contain any inference logic itself

Main API:

from Framework.predict import predict
predict(
    weights="weights/yolov8_assem.pt",
    tif="examples/sample.tif",
    output=None,        # auto-generate runs/predictN/result.shp
    conf=0.25,
)

Why split it from detector.py: predict.py deals with the user-facing interface (paths, logs), while detector.py deals with the algorithm. This
separation makes detector.py reusable as a library and easier to test.

---

## detector.py

The core sliding-window detection engine. This is the only module that actually performs inference on a GeoTIFF. It has no dependency on
predict.py and can be imported on its own.

Pipeline:
1. Open the GeoTIFF with rasterio and read its geotransform and CRS.
2. Slide a window of size tile x tile with step stride across the raster.
3. For each tile, apply a per-channel percentile stretch to 0-255 RGB.
4. Convert RGB to BGR for Ultralytics input.
5. Run YOLO inference on the tile.
6. Map each detection back to geographic coordinates using the window's
   affine transform.
7. After all tiles, apply spatial non-maximum suppression (STRtree-based)
   to merge overlapping boxes of the same class.
8. Write the final result as an ESRI Shapefile.

Public functions:

- detect_to_shp(tif_path, model_path, out_shp, ...)
  End-to-end detection from GeoTIFF to Shapefile.

- sliding_windows(width, height, tile_size, stride, edge_policy)
  Generator that yields (x, y, Window) tuples covering the raster.

- percent_stretch_per_tile(tile_f32, lower, upper, gamma)
  Per-tile contrast normalization.

- spatial_nms(gdf, iou_thr)
  STRtree-accelerated spatial NMS. Keeps the highest-confidence box among
  overlapping boxes of the same class.

- save_as_shapefile(gdf, out_shp)
  Writes the GeoDataFrame with fields: cls, conf, class, geometry.

Main API:

from Framework.detector import detect_to_shp
detect_to_shp(
    tif_path="examples/sample.tif",
    model_path="weights/yolov8_assem.pt",
    out_shp="runs/predict1/result.shp",
    tile_size=512,
    stride=480,
    conf_th=0.25,
)

Notes:
- The Shapefile inherits the CRS of the input GeoTIFF. If your raster is in
  WGS84, the output will be in WGS84 as well.
- The percent stretch is computed per tile, not over the whole raster. This
  keeps local contrast stable across large scenes.
- The spatial NMS uses shapely's STRtree, which scales to thousands of boxes
  without a noticeable slowdown.