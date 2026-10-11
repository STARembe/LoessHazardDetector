"""
Validation entry point for LoessHazardDetector.
"""

from ultralytics import YOLO

from Framework.logger import get_logger, section

log = get_logger()


def validate(
    weights: str,
    data: str,
    split: str = "val",
    plots: bool = False,
    save_json: bool = False,
    device: str = None,
    project: str = "runs",
    name: str = "val",
):
    """
    Validate a YOLO model.

    Args:
        weights:   path to model weights.
        data:      dataset yaml path.
        split:     dataset split to evaluate (val / test).
        plots:     generate validation plots.
        save_json: export predictions in COCO JSON.
        project:   output directory.
        name:      experiment name.
    """
    section("LoessHazardDetector :: Validation")
    log.info("Weights        : %s", weights)
    log.info("Dataset        : %s", data)
    log.info("Split          : %s", split)
    log.info("Generate plots : %s", plots)
    log.info("Save JSON      : %s", save_json)

    log.info("Loading model ...")
    model = YOLO(weights)
    log.info("Model loaded.")

    log.info("Running validation ...")
    results = model.val(
        data=data,
        split=split,
        plots=plots,
        save_json=save_json,
        device=device,
        project=project,
        name=name,
    )
    log.info("Validation finished. Results saved under: %s/%s", project, name)
    return results