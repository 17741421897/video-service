"""自动查找引擎：优先本目录内的 ComfyUI，再兼容旧布局。"""
from __future__ import annotations

from pathlib import Path

from engine_paths import resolve_engine
from models_config import DEFAULT_GGUF, DEFAULT_T5, DEFAULT_VAE

# 旧布局：与 video-service 同级的文件夹名
LEGACY_SIBLING_NAMES = ("video-engine", "wan-engine", "engine")

_WAN_MODEL_TRIPLE = (
    ("diffusion_models", DEFAULT_GGUF),
    ("text_encoders", DEFAULT_T5),
    ("vae", DEFAULT_VAE),
)


def _try_engine_root(cand: Path) -> Path | None:
    if not cand.is_dir():
        return None
    try:
        resolve_engine(cand)
        return cand.resolve()
    except FileNotFoundError:
        return None


def wan_models_complete(models_dir: Path) -> bool:
    """三个默认 Wan 模型是否都在同一 models 根下。"""
    root = models_dir.resolve()
    for sub, name in _WAN_MODEL_TRIPLE:
        p = root / sub / name
        if not p.is_file() or p.stat().st_size <= 0:
            return False
    return True


def _engine_candidates(pkg: Path) -> list[Path]:
    """可能作为 ENGINE_ROOT 的目录（去重、保持优先级）。"""
    seen: set[Path] = set()
    out: list[Path] = []

    def add(cand: Path) -> None:
        hit = _try_engine_root(cand)
        if hit is not None and hit not in seen:
            seen.add(hit)
            out.append(hit)

    for cand in (pkg, pkg / "engine"):
        add(cand)

    parent = pkg.parent
    for name in LEGACY_SIBLING_NAMES:
        add(parent / name)

    return out


def detect_engine(package_root: Path | None = None) -> Path:
    """
    查找 ComfyUI 引擎目录；若安装目录下 models 为空，优先选用已放齐模型的上级目录。
    """
    import os

    pkg = (package_root or Path(__file__).resolve().parent).resolve()
    env = os.environ.get("ENGINE_ROOT", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        resolve_engine(root)
        return root

    candidates = _engine_candidates(pkg)
    if not candidates:
        raise FileNotFoundError(
            "找不到 ComfyUI 引擎。请把 ComfyUI 文件夹放在 video-service 目录下（含 main.py）。"
        )

    for er in candidates:
        _, _, models_dir = resolve_engine(er)
        if wan_models_complete(models_dir):
            return er

    return candidates[0]
