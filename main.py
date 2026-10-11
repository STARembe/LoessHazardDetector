"""
LoessHazardDetector :: Command Line Interface

Tasks:
    train    Train a YOLO model
    val      Validate a YOLO model
    predict  Run detection on a GeoTIFF and export a Shapefile

Configuration priority (low to high):
    1. configs/default.yaml
    2. --config <user.yaml>
    3. command-line arguments
"""

import argparse

from Framework.config import load_config, DEFAULT_CONFIG_PATH
from Framework.train import train
from Framework.validate import validate
from Framework.predict import predict
from Framework.model_registry import list_models
from Framework.logger import get_logger

log = get_logger()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lhd",
        description="LoessHazardDetector: geohazard detection in the Chinese Loess Plateau",
    )

    # ------------------ task ------------------
    parser.add_argument(
        "task",
        choices=["train", "val", "predict"],
        help="Task to run",
    )

    # ------------------ config ------------------
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to a YAML configuration file (default: {DEFAULT_CONFIG_PATH})",
    )

    # ------------------ shared ------------------
    parser.add_argument("--model", default=argparse.SUPPRESS,
                        help="Model name (default: yolov8_assem)")
    parser.add_argument("--weights", default=argparse.SUPPRESS,
                        help="Path to a weight file (default: weights/yolov8_assem.pt)")
    parser.add_argument("--data", default=argparse.SUPPRESS,
                        help="Dataset YAML path (default: data/landslide.yaml)")
    parser.add_argument("--device", default=argparse.SUPPRESS,
                        help="Device, e.g. cuda:0 or cpu (default: auto-detect)")

    # ------------------ train ------------------
    parser.add_argument("--pretrained", action="store_true", default=argparse.SUPPRESS,
                        help="Initialize from the default pretrained weight")
    parser.add_argument("--epochs", type=int, default=argparse.SUPPRESS,
                        help="Training epochs (default: 350)")
    parser.add_argument("--lr0", type=float, default=argparse.SUPPRESS,
                        help="Initial learning rate (default: 0.001)")
    parser.add_argument("--batch", type=int, default=argparse.SUPPRESS,
                        help="Batch size (default: 8)")
    parser.add_argument("--workers", type=int, default=argparse.SUPPRESS,
                        help="DataLoader workers (default: 8)")

    # ------------------ val ------------------
    parser.add_argument("--split", default=argparse.SUPPRESS,
                        choices=["val", "test"],
                        help="Dataset split (default: val)")
    parser.add_argument("--plots", action="store_true", default=argparse.SUPPRESS,
                        help="Generate validation plots")
    parser.add_argument("--save-json", action="store_true", default=argparse.SUPPRESS,
                        help="Export validation predictions as COCO JSON")

    # ------------------ predict ------------------
    parser.add_argument("--tif", default=argparse.SUPPRESS,
                        help="Input GeoTIFF path (default: examples/sample.tif)")
    parser.add_argument("--out", default=argparse.SUPPRESS,
                        help="Output Shapefile path (default: runs/predictN/result.shp)")
    parser.add_argument("--tile", type=int, default=argparse.SUPPRESS,
                        help="Sliding-window tile size (default: 512)")
    parser.add_argument("--stride", type=int, default=argparse.SUPPRESS,
                        help="Sliding-window stride (default: 480)")
    parser.add_argument("--edge-policy", default=argparse.SUPPRESS,
                        choices=["include_last", "skip_small_tail", "single_tile"],
                        help="Edge handling policy (default: include_last)")
    parser.add_argument("--band-order", default=argparse.SUPPRESS,
                        help="R,G,B band indices, 1-based (default: 1,2,3)")
    parser.add_argument("--lower", type=float, default=argparse.SUPPRESS,
                        help="Lower percentile for contrast stretch (default: 5.0)")
    parser.add_argument("--upper", type=float, default=argparse.SUPPRESS,
                        help="Upper percentile for contrast stretch (default: 95.0)")
    parser.add_argument("--gamma", type=float, default=argparse.SUPPRESS,
                        help="Optional gamma correction (default: none)")
    parser.add_argument("--imgsz", type=int, default=argparse.SUPPRESS,
                        help="YOLO input size (default: 512)")
    parser.add_argument("--conf", type=float, default=argparse.SUPPRESS,
                        help="Confidence threshold (default: 0.25)")
    parser.add_argument("--merge-iou", type=float, default=argparse.SUPPRESS,
                        help="Spatial NMS IoU threshold (default: 0.5)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config(args, task=args.task)

    if args.task == "train":
        train(
            model_name=cfg["model"]["name"],
            data=cfg["data"]["yaml"],
            pretrained=cfg["model"]["pretrained"],
            weights=cfg["model"]["weights"],
            epochs=cfg["train"]["epochs"],
            lr0=cfg["train"]["lr0"],
            imgsz=cfg["train"]["imgsz"],
            batch=cfg["train"]["batch"],
            workers=cfg["train"]["workers"],
            device=cfg.get("device"),
        )

    elif args.task == "val":
        validate(
            weights=cfg["model"]["weights"],
            data=cfg["data"]["yaml"],
            split=cfg["val"]["split"],
            plots=cfg["val"]["plots"],
            save_json=cfg["val"]["save_json"],
            device=cfg.get("device"),
        )

    elif args.task == "predict":
        band_order = tuple(cfg["predict"]["band_order"])
        predict(
            weights=cfg["model"]["weights"],
            tif=cfg["predict"]["tif"],
            output=cfg["predict"]["out"],
            band_order=band_order,
            tile=cfg["predict"]["tile"],
            stride=cfg["predict"]["stride"],
            edge_policy=cfg["predict"]["edge_policy"],
            lower=cfg["predict"]["lower"],
            upper=cfg["predict"]["upper"],
            gamma=cfg["predict"]["gamma"],
            imgsz=cfg["predict"]["imgsz"],
            conf=cfg["predict"]["conf"],
            merge_iou=cfg["predict"]["merge_iou"],
            device=cfg.get("device"),
        )


if __name__ == "__main__":
    main()