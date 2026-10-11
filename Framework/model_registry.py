"""
Model Registry

Manage supported YOLO architectures and their default weights.

Supported models:
    - yolov5
    - yolov8
    - yolo11
    - yolov8_assem   (custom AssemFormer variant)

Each entry defines:
    - yaml:           architecture configuration
    - default_weight: pretrained weight used when --pretrained is set
"""

MODEL_REGISTRY = {

    "yolov5": {
        "yaml": "ultralytics/cfg/models/v5/yolov5.yaml",
        "default_weight": None,
    },

    "yolov8": {
        "yaml": "ultralytics/cfg/models/v8/yolov8.yaml",
        "default_weight": "weights/yolov8n.pt",
    },

    "yolo11": {
        "yaml": "ultralytics/cfg/models/11/yolo11.yaml",
        "default_weight": "weights/yolo11n.pt",
    },

    "yolov8_assem": {
        "yaml": "ultralytics/cfg/models/v8/yolov8-assemformer.yaml",
        "default_weight": "weights/yolov8_assem.pt",
    },
}


def get_model_config(model_name):
    """Return yaml path and default weight for a given model name."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unsupported model: {model_name}\n"
            f"Available: {list(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[model_name]


def list_models():
    """Return list of supported model names."""
    return list(MODEL_REGISTRY.keys())