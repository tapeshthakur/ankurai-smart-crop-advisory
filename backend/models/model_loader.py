from __future__ import annotations

import glob
import pickle
import re
from pathlib import Path
from typing import Any, List, Tuple

import joblib
from config import settings


VERSION_PATTERN = re.compile(r"_v(\d{8}_\d{6})\.pkl$")


def _ml_dir() -> Path:
    """
    Resolve ../ml from backend directory:
    project/
      backend/models/model_loader.py
      ml/
    """
    return settings.ml_dir


def _candidate_paths(pattern: str) -> List[Path]:
    ml_root = _ml_dir()
    search_pattern = str(ml_root / "**" / pattern)
    return [Path(p) for p in glob.glob(search_pattern, recursive=True)]


def _version_key(path: Path) -> Tuple[int, str]:
    match = VERSION_PATTERN.search(path.name)
    if match:
        return (1, match.group(1))
    return (0, path.name)


def _load_model_path(path: Path) -> Any:
    try:
        return joblib.load(path)
    except Exception:
        with path.open("rb") as fp:
            return pickle.load(fp)


def _load_latest(pattern: str, model_label: str) -> Any:
    candidates = _candidate_paths(pattern)
    if not candidates:
        raise FileNotFoundError(
            f"No {model_label} model found in '{_ml_dir()}' with pattern '{pattern}'."
        )

    latest = sorted(candidates, key=_version_key, reverse=True)[0]
    return _load_model_path(latest)


def load_latest_classifier() -> Any:
    """Load latest versioned classifier model."""
    candidates = [
        path
        for path in _candidate_paths("rf_classifier_*_v*.pkl")
        if "pest_outbreak" not in path.parts and "outbreak_next_7d" not in path.name
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No crop classifier model found in '{_ml_dir()}' with pattern 'rf_classifier_*_v*.pkl'."
        )
    latest = sorted(candidates, key=_version_key, reverse=True)[0]
    return _load_model_path(latest)


def load_latest_regressor() -> Any:
    """Load latest versioned regressor model."""
    return _load_latest("rf_regressor_*_v*.pkl", "regressor")


def load_latest_pest_outbreak_classifier() -> Any:
    """Load latest pest-outbreak classifier model."""
    return _load_latest("rf_classifier_outbreak_next_7d_v*.pkl", "pest outbreak classifier")
