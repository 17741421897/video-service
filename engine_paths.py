"""Resolve engine layout: video-engine/ (flat) or .../ComfyUI/."""
from __future__ import annotations

from pathlib import Path


def resolve_engine(engine_root: Path) -> tuple[Path, Path, Path]:
    """
    Returns (engine_root, comfy_dir, models_dir).
    comfy_dir is where main.py lives.
    """
    er = engine_root.expanduser().resolve()
    if (er / "main.py").is_file():
        return er, er, er / "models"
    comfy = er / "ComfyUI"
    if (comfy / "main.py").is_file():
        return er, comfy, comfy / "models"
    raise FileNotFoundError(f"Invalid ENGINE_ROOT (no main.py): {er}")
