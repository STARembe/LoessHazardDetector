# data/

This folder holds dataset configuration files and a small example dataset.

---

## Contents

data/
├── README.md           # this file
├── landslide.yaml      # dataset config for the Loess Plateau training set
└── example/            # a small example dataset for format reference
    ├── images/
    │   └── sample.jpg
    ├── labels/
    │   └── sample.txt
    ├── train.txt
    ├── val.txt
    └── test.txt


---

## YOLO dataset format

### Directory layout

A minimal YOLO dataset looks like this:

data/example/
├── images/                 # image files (.jpg, .png, .tif, ...)
│   └── sample.jpg
├── labels/                 # one .txt per image, same base name
│   └── sample.txt
├── train.txt               # list of training image paths
├── val.txt                 # list of validation image paths
└── test.txt                # list of test image paths

The folder names (images, labels) are conventional but not enforced. What matters is that the three txt files list valid image paths.

### Label file format

Each label file has one line per object. Each line contains five values:

class_id  x_center  y_center  width  height

All coordinates are normalized to [0, 1] relative to the image size. The origin (0, 0) is the top-left corner.

Example, one label file with two objects:

0 0.523 0.418 0.152 0.203
1 0.781 0.642 0.091 0.118

For this project, class IDs are:

0 = landslide (L)
1 = mining-induced subsidence (M)

So the first line above is a landslide, and the second is a subsidence zone.

If an image contains no objects, the label file should exist but be empty.
Ultralytics treats it as a background image.

### TXT list files

train.txt, val.txt, and test.txt each contain one image path per line.
Paths can be absolute or relative to the "path" field in the dataset YAML.

Example, train.txt:

example/images/sample.jpg

A real training set contains many lines, one per image.

---

## Dataset YAML

The dataset YAML tells Ultralytics where to find the images and how many classes to expect. A template is provided at data/landslide.yaml.

### Two supported layouts

Layout A — TXT list mode (used in this project):

path: /root/autodl-tmp/dataset1
train: train.txt
val:   val.txt
test:  test.txt
nc: 2
names: ['L', 'M']

In this mode, train.txt / val.txt / test.txt contain image paths. Relative paths are resolved against "path".

Layout B — Directory mode:

path: /path/to/dataset
train: images/train
val:   images/val
test:  images/test
nc: 2
names: ['L', 'M']

In this mode, Ultralytics scans the given directory for images and looks for matching label files in a parallel labels/ folder.

Both layouts are supported. The example in data/landslide.yaml uses Layout A.

### Fields

| Field | Type   | Description                                    |
|-------|--------|------------------------------------------------|
| path  | string | Dataset root directory                         |
| train | string | Training split (txt file or image folder)      |
| val   | string | Validation split                               |
| test  | string | Test split (optional but recommended)          |
| nc    | int    | Number of classes                              |
| names | list   | Class names, in order of class ID              |

---

## Preparing your own dataset

1. Copy data/landslide.yaml to a new file, for example data/my_site.yaml.
2. Edit the "path" field to point to your dataset root.
3. If your txt files are named differently, edit the train / val / test lines accordingly.
4. If your dataset uses different class names or a different number of classes, update nc and names.
5. Run training with --data data/my_site.yaml.

Example:

python main.py train --model yolov8_assem --data data/my_site.yaml

---

## Notes on georeferencing

YOLO-format images do not carry georeference information. This is fine for training: the model learns to detect deformation patterns in image space.

For prediction on real data, use a GeoTIFF instead. The predict task reads the geotransform and coordinate system from the raster, converts each
detection back to geographic coordinates, and writes the result as a Shapefile. This keeps the output usable in QGIS, ArcGIS, or Python GIS tools.

In short:

- Training and validation: YOLO-format images (no georeference required)
- Prediction: GeoTIFF (georeference required), output as Shapefile