"""
Core detection engine for LoessHazardDetector.

Pipeline:
    1. Slide a window over the input GeoTIFF.
    2. Per-tile percentile stretch to 0-255 RGB.
    3. Convert RGB -> BGR for Ultralytics input.
    4. Run YOLO inference.
    5. Map pixel boxes back to geographic coordinates.
    6. Spatial NMS and export to Shapefile.
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import Affine
import geopandas as gpd
from shapely.geometry import box
from shapely.strtree import STRtree
from ultralytics import YOLO
import torch

from Framework.logger import get_logger

log = get_logger()


# ---------------- helpers ----------------

def sliding_windows(width, height, tile_size=512, stride=480, edge_policy="include_last"):
    """
    Generate sliding windows over an image.

    edge_policy:
        - include_last:    always include the last tile, aligned to the edge
        - skip_small_tail: skip the last tile if the remaining gap < 32 px
        - single_tile:     only yield the top-left tile
    """
    if edge_policy == "single_tile":
        yield 0, 0, Window(0, 0, tile_size, tile_size)
        return

    xs = list(range(0, max(1, width - tile_size + 1), stride))
    ys = list(range(0, max(1, height - tile_size + 1), stride))

    last_x = width - tile_size
    last_y = height - tile_size

    if xs[-1] != last_x:
        if edge_policy == "include_last":
            xs.append(max(0, last_x))
        elif edge_policy == "skip_small_tail":
            if (last_x - xs[-1]) >= 32:
                xs.append(max(0, last_x))

    if ys[-1] != last_y:
        if edge_policy == "include_last":
            ys.append(max(0, last_y))
        elif edge_policy == "skip_small_tail":
            if (last_y - ys[-1]) >= 32:
                ys.append(max(0, last_y))

    for y in ys:
        for x in xs:
            yield x, y, Window(x, y, tile_size, tile_size)


def percent_stretch_per_tile(tile_f32: np.ndarray, lower=5, upper=95, gamma=None) -> np.ndarray:
    """Per-tile percentile stretch to uint8 RGB."""
    out = np.zeros_like(tile_f32, dtype=np.uint8)
    for i in range(tile_f32.shape[2]):
        band = tile_f32[:, :, i]
        valid = np.isfinite(band)
        if not np.any(valid):
            continue
        vmin, vmax = np.percentile(band[valid], (lower, upper))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
            vmin, vmax = np.nanmin(band[valid]), np.nanmax(band[valid])
            if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
                continue
        norm = (band - vmin) / (vmax - vmin + 1e-9)
        norm = np.clip(norm, 0, 1)
        if gamma is not None:
            norm = np.power(norm, float(gamma))
        out[:, :, i] = (norm * 255.0).astype(np.uint8)
    return out


def xyxy_pixels_to_geo(xyxy, transform: Affine):
    """Convert a pixel-space xyxy box to a geographic shapely box."""
    xmin, ymin, xmax, ymax = xyxy
    pts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    gx = [transform * (p[0], p[1]) for p in pts]
    xs = [p[0] for p in gx]
    ys = [p[1] for p in gx]
    return box(min(xs), min(ys), max(xs), max(ys))


def spatial_nms(gdf: gpd.GeoDataFrame, iou_thr: float = 0.5) -> gpd.GeoDataFrame:
    """
    Spatial NMS using STRtree for O(n log n) performance.

    Keeps the highest-confidence box among overlapping same-class boxes.
    """
    if gdf.empty:
        return gdf

    g = gdf.copy().reset_index(drop=True)
    g["area"] = g.geometry.area

    kept_indices = []

    # Process each class independently
    for cls_id in g["cls"].unique():
        sub = g[g["cls"] == cls_id].copy()
        # Sort by confidence descending, area descending
        sub = sub.sort_values(["conf", "area"], ascending=[False, False]).reset_index()

        geoms = sub.geometry.values
        tree = STRtree(geoms)
        n = len(sub)
        suppressed = np.zeros(n, dtype=bool)

        for i in range(n):
            if suppressed[i]:
                continue
            kept_indices.append(sub.loc[i, "index"])

            # Query candidates whose bbox intersects
            cand_idx = tree.query(geoms[i])
            cand_idx = cand_idx[cand_idx > i]  # only boxes after i (lower conf)

            gi = geoms[i]
            area_i = sub.loc[i, "area"]

            for j in cand_idx:
                if suppressed[j]:
                    continue
                inter = gi.intersection(geoms[j]).area
                if inter == 0:
                    continue
                denom = area_i + sub.loc[j, "area"] - inter + 1e-9
                iou = inter / denom
                if iou >= iou_thr:
                    suppressed[j] = True

    result = g.loc[kept_indices].drop(columns=["area"]).reset_index(drop=True)
    return result

def save_as_shapefile(gdf: gpd.GeoDataFrame, out_shp: str):
    """Write a GeoDataFrame to ESRI Shapefile with ASCII-safe fields."""
    os.makedirs(os.path.dirname(os.path.abspath(out_shp)), exist_ok=True)
    if gdf.empty:
        gdf = gpd.GeoDataFrame({"cls": [], "conf": [], "class": []}, geometry=[], crs=gdf.crs)
    gdf = gdf[["cls", "conf", "class", "geometry"]].copy()
    gdf["cls"] = gdf["cls"].astype(np.int32)
    gdf["conf"] = gdf["conf"].astype(float)
    gdf["class"] = gdf["class"].astype(str).str[:1]
    gdf.to_file(out_shp, driver="ESRI Shapefile")
    log.info("Saved SHP: %s (features=%d)", out_shp, len(gdf))


# ---------------- main entry ----------------

def detect_to_shp(
    tif_path: str,
    model_path: str,
    out_shp: str,
    band_order=(1, 2, 3),
    tile_size: int = 512,
    stride: int = 480,
    edge_policy: str = "include_last",
    lower_pct: float = 5.0,
    upper_pct: float = 95.0,
    gamma: float = None,
    imgsz: int = 512,
    conf_th: float = 0.25,
    merge_iou: float = 0.5,
    device: str = None,
):
    """
    Run sliding-window detection on a GeoTIFF and export results as a Shapefile.
    """
    device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    use_half = device != "cpu"
    log.info("Device: %s, half=%s", device, use_half)

    model = YOLO(model_path)
    model.to(device=device)

    # Class id -> letter (L = landslide, M = mining subsidence)
    names = getattr(model.model, "names", None) or getattr(model, "names", {})
    id2letter = {}
    for k, v in (names or {}).items():
        name = str(v).lower()
        if name in ("l", "ls", "land", "landslide") or "滑坡" in name:
            id2letter[int(k)] = "L"
        elif name in ("m", "ms", "subs", "subsidence") or "沉降" in name:
            id2letter[int(k)] = "M"
    if not id2letter:
        id2letter = {0: "L", 1: "M"}
    log.info("Class mapping: %s", id2letter)

    with rasterio.open(tif_path) as ds:
        width, height = ds.width, ds.height
        transform0, crs = ds.transform, ds.crs
        log.info("Input raster: %d x %d px, %d bands", width, height, ds.count)

        # Pre-compute tile grid
        tiles = list(sliding_windows(width, height, tile_size, stride, edge_policy))
        log.info("Tiles generated: %d", len(tiles))

        recs = []
        for idx, (x0, y0, win) in enumerate(tiles, 1):
            if idx % 50 == 0 or idx == 1 or idx == len(tiles):
                log.info("Tile %d/%d ...", idx, len(tiles))

            tile = ds.read(indexes=band_order, window=win, boundless=True,
                           fill_value=np.nan).astype(np.float32)
            tile = np.transpose(tile, (1, 2, 0))

            tile_rgb_u8 = percent_stretch_per_tile(tile, lower_pct, upper_pct, gamma=gamma)
            tile_bgr_u8 = tile_rgb_u8[..., ::-1].copy()

            preds = model.predict(
                source=tile_bgr_u8,
                imgsz=imgsz,
                conf=conf_th,
                iou=0.5,
                device=device,
                half=use_half,
                max_det=500,
                agnostic_nms=True,
                verbose=False,
            )

            tile_tf = rasterio.windows.transform(win, transform0)

            for r in preds:
                if r.boxes is None or len(r.boxes) == 0:
                    continue
                boxes = r.boxes.xyxy.cpu().numpy()
                clss = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy().astype(float)
                for b, c, cf in zip(boxes, clss, confs):
                    geom = xyxy_pixels_to_geo(b, tile_tf)
                    recs.append({
                        "cls": int(c),
                        "conf": float(cf),
                        "class": id2letter.get(int(c), "L"),
                        "geometry": geom,
                    })

        gdf = gpd.GeoDataFrame(recs, geometry="geometry", crs=crs)
        log.info("Raw detections: %d", len(gdf))
        if not gdf.empty:
            gdf = spatial_nms(gdf, iou_thr=merge_iou)
            log.info("After NMS: %d", len(gdf))
        save_as_shapefile(gdf, out_shp)
        return gdf