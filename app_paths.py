"""安装根目录（源码运行）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def install_root() -> Path:
    """API 与 workflow 所在目录（video-service 根）。"""
    env = os.environ.get("VIDEO_PACKAGE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


