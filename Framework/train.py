"""
Training entry point for LoessHazardDetector.

All hyperparameters are exposed through CLI and can be overridden.
"""

from ultralytics import YOLO

from Framework.model_registry import get_model_config
from Framework.logger import get_logger, section, subsection

log = get_logger()


def train(
    model_name: str = "yolov8_assem",
    data: str = "data/landslide.yaml",
    pretrained: bool = False,
    weights: str = None,
    epochs: int = 350,
    lr0: float = 0.001,
    imgsz: int = 512,
    batch: int = 8,
    workers: int = 8,
    device: str = None,
    project: str = "runs",
    name: str = "train",
):
    """
    Train a YOLO model.

    Args:
        model_name: architecture name (see model_registry).
        data:       dataset yaml path.
        pretrained: load default pretrained weight if available.
        weights:    explicit weight path (overrides pretrained).
        epochs:     training epochs.
        lr0:        initial learning rate.
        imgsz:      input image size.
        batch:      batch size.
        workers:    dataloader workers.
        project:    output project directory.
        name:       experiment name.
    """
    cfg = get_model_config(model_name)
    model_yaml = cfg["yaml"]
    default_weight = cfg["default_weight"]

    section("LoessHazardDetector :: Training")
    log.info("Model name     : %s", model_name)
    log.info("Model yaml     : %s", model_yaml)
    log.info("Dataset        : %s", data)
    log.info("Pretrained     : %s", pretrained)
    log.info("Custom weights : %s", weights)
    subsection("Hyperparameters")
    log.info("Epochs         : %d", epochs)
    log.info("LR0            : %g", lr0)
    log.info("Image size     : %d", imgsz)
    log.info("Batch size     : %d", batch)
    log.info("Workers        : %d", workers)

    # ------------------------------------------------
    # Model initialization
    # Priority:
    #   1. user weights  (fine-tune from arbitrary checkpoint)
    #   2. default weight (pretrained initialization)
    #   3. random init    (from yaml)
    # ------------------------------------------------
    if weights is not None:
        log.info("Initializing from user weights: %s", weights)
        model = YOLO(model_yaml)
        model.load(weights)
    elif pretrained and default_weight is not None:
        log.info("Initializing from default weight: %s", default_weight)
        model = YOLO(default_weight)
    else:
        log.info("Initializing from yaml (random init)")
        model = YOLO(model_yaml)

    model.info()

    subsection("Start training")
    results = model.train(
        data=data,
        epochs=epochs,
        lr0=lr0,
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        device=device, 
        optimizer="AdamW",
        project=project,
        name=name,
    )
    log.info("Training finished. Results saved under: %s/%s", project, name)
    return results