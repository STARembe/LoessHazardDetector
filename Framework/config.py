"""
Configuration loader for LoessHazardDetector.

The final configuration is built in three layers, from lowest to highest
priority:

    1. configs/default.yaml
    2. a user YAML passed via --config
    3. command-line arguments

Command-line arguments use argparse.SUPPRESS as their default, so that only
values explicitly provided by the user appear in the namespace. This lets us
distinguish "user did not set this" from "user set it to the default value".
"""

from pathlib import Path
import argparse
import yaml


DEFAULT_CONFIG_PATH = Path("configs/default.yaml")


# Map flat CLI argument names to their nested position in the config dict.
# 'imgsz' is handled separately because it belongs to different sections
# depending on the task.
CLI_TO_CONFIG = {
    # model
    "model":       ("model", "name"),
    "weights":     ("model", "weights"),
    "pretrained":  ("model", "pretrained"),
    # data
    "data":        ("data", "yaml"),
    # train
    "epochs":      ("train", "epochs"),
    "lr0":         ("train", "lr0"),
    "batch":       ("train", "batch"),
    "workers":     ("train", "workers"),
    # val
    "split":       ("val", "split"),
    "plots":       ("val", "plots"),
    "save_json":   ("val", "save_json"),
    # predict
    "tif":         ("predict", "tif"),
    "out":         ("predict", "out"),
    "tile":        ("predict", "tile"),
    "stride":      ("predict", "stride"),
    "edge_policy": ("predict", "edge_policy"),
    "band_order":  ("predict", "band_order"),
    "lower":       ("predict", "lower"),
    "upper":       ("predict", "upper"),
    "gamma":       ("predict", "gamma"),
    "conf":        ("predict", "conf"),
    "merge_iou":   ("predict", "merge_iou"),
    # runtime
    "device":      ("device",),
}


def load_config(cli_args: argparse.Namespace, task: str) -> dict:
    """
    Build the final configuration dict.

    Args:
        cli_args: parsed argparse Namespace.
        task:     one of 'train', 'val', 'predict'.

    Returns:
        Nested dict with sections: model, data, train, val, predict, device.
    """
    cfg = _read_yaml(DEFAULT_CONFIG_PATH)

    # Layer 2: user config
    user_path = getattr(cli_args, "config", None)
    if user_path and Path(user_path).resolve() != DEFAULT_CONFIG_PATH.resolve():
        cfg = _deep_merge(cfg, _read_yaml(Path(user_path)))

    # Layer 3: CLI overrides
    overrides = _cli_to_nested(vars(cli_args), task)
    if overrides:
        cfg = _deep_merge(cfg, overrides)

    return cfg


def _read_yaml(path: Path) -> dict:
    """Read a YAML file. Return an empty dict if the file does not exist."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Returns a new dict."""
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _cli_to_nested(cli_dict: dict, task: str) -> dict:
    """
    Convert a flat argparse namespace into a nested override dict.

    Skips 'task' and 'config', and handles 'imgsz' specially because it
    belongs to the section matching the current task.
    """
    nested = {}

    for key, value in cli_dict.items():
        if key in ("task", "config"):
            continue

        if key == "imgsz":
            if task == "train":
                nested.setdefault("train", {})["imgsz"] = value
            elif task == "predict":
                nested.setdefault("predict", {})["imgsz"] = value
            continue

        path = CLI_TO_CONFIG.get(key)
        if path is None:
            continue

        # walk to the parent dict
        node = nested
        for part in path[:-1]:
            node = node.setdefault(part, {})
        node[path[-1]] = value

    return nested