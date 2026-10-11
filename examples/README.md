# examples/

This folder contains a small sample GeoTIFF for testing the predict task.

---

## Contents

examples/
├── README.md
└── sample.tif

---

## sample.tif

A small GeoTIFF clipped from Hualong County, Qinghai Province, China.
Coordinate system: WGS84 (EPSG:4326).

The raster has three bands, in this order:

| Band | Content              |
|------|----------------------|
| 1    | PGS deformation      |
| 2    | Slope                |
| 3    | DEM                  |

This is the same band order expected by the default configuration in
configs/default.yaml (band_order: [1, 2, 3]).

---

## What it is used for

The predict task accepts a GeoTIFF of any size. LoessHazardDetector slides a
window over the raster, runs the detector on each tile, and maps every
detection back to geographic coordinates. The final output is an ESRI
Shapefile that preserves the coordinate system of the input raster.

This means you can run the detector directly on a large GeoTIFF covering an
entire study area, and the output Shapefile can be opened in QGIS, ArcGIS,
or any Python GIS library without further conversion.

The sample in this folder is small enough to be processed in a few seconds,
so it is a good way to verify that the toolkit is installed correctly.

---

## Trying it out

Run prediction with the default configuration. It uses sample.tif
automatically:

python main.py predict

Output goes to runs/predict1/result.shp.

To use your own raster instead:

python main.py predict --tif /path/to/your.tif

Your GeoTIFF must:

- contain three bands (PGS deformation, slope, DEM, in that order by default)
- contain georeference information (coordinate system and geotransform)

If your band order is different, change band_order in configs/default.yaml.