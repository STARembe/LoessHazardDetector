"""
Prediction entry point for LoessHazardDetector.
"""

import os
from pathlib import Path

from Framework.detector import detect_to_shp
from Framework.logger import get_logger, section, subsection

log = get_logger()


def next_run_dir(base: str, prefix: str) -> Path:
    """Return base/<prefix>N with the smallest unused N >= 1."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    n = 1
    while (base / f"{prefix}{n}").exists():
        n += 1
    return base / f"{prefix}{n}"


def predict(
    weights: str,
    tif: str,
    output: str = None,
    band_order=(1, 2, 3),
    tile: int = 512,
    stride: int = 480,
    edge_policy: str = "include_last",
    lower: float = 5.0,
    upper: float = 95.0,
    gamma: float = None,
    imgsz: int = 512,
    conf: float = 0.25,
    merge_iou: float = 0.5,
    device: str = None,
):
    """Run detection on a GeoTIFF and export to Shapefile."""
    section("LoessHazardDetector :: Prediction")
    log.info("Model      : %s", weights)
    log.info("Input      : %s", tif)

    # Auto-generate output path if not provided by user
    if output is None:
        run_dir = next_run_dir("runs", "predict")
        output = str(run_dir / "result.shp")
        log.info("Output     : %s (auto)", output)
    else:
        log.info("Output     : %s", output)

    subsection("Parameters")
    log.info("Tile       : %d", tile)
    log.info("Stride     : %d", stride)
    log.info("Edge policy: %s", edge_policy)
    log.info("Bands      : %s", band_order)
    log.info("Stretch    : lower=%g, upper=%g, gamma=%s", lower, upper, gamma)
    log.info("Image size : %d", imgsz)
    log.info("Confidence : %g", conf)
    log.info("Merge IoU  : %g", merge_iou)

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)

    detect_to_shp(
        tif_path=tif,
        model_path=weights,
        out_shp=output,
        band_order=band_order,
        tile_size=tile,
        stride=stride,
        edge_policy=edge_policy,
        lower_pct=lower,
        upper_pct=upper,
        gamma=gamma,
        imgsz=imgsz,
        conf_th=conf,
        merge_iou=merge_iou,
        device=device,
    )