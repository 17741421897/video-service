"""图生视频：解码 Base64 并写入 ComfyUI input 目录。"""
from __future__ import annotations

import base64
import re
from pathlib import Path

_MAX_BYTES = 15 * 1024 * 1024


def decode_image_base64(data: str) -> bytes:
    s = str(data or "").strip()
    if not s:
        raise ValueError("image_base64 为空")
    if "," in s and s.lower().startswith("data:"):
        s = s.split(",", 1)[1]
    s = re.sub(r"\s+", "", s)
    try:
        raw = base64.b64decode(s, validate=False)
    except Exception as e:
        raise ValueError(f"image_base64 解码失败: {e}") from e
    if not raw:
        raise ValueError("image_base64 解码后为空")
    if len(raw) > _MAX_BYTES:
        raise ValueError(f"图片过大（>{_MAX_BYTES // (1024 * 1024)}MB）")
    return raw


def _guess_ext(raw: bytes) -> str:
    if raw[:3] == b"\xff\xd8\xff":
        return "jpg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if raw[:4] == b"RIFF" and len(raw) > 12 and raw[8:12] == b"WEBP":
        return "webp"
    return "png"


def write_comfy_input_image(raw: bytes, comfy_dir: Path, job_id: str) -> str:
    """返回 LoadImage 所需的文件名（位于 ComfyUI/input/）。"""
    inp = comfy_dir / "input"
    inp.mkdir(parents=True, exist_ok=True)
    ext = _guess_ext(raw)
    name = f"xiaozi_i2v_{job_id}.{ext}"
    (inp / name).write_bytes(raw)
    return name
