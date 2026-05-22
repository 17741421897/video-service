"""贤紫视频编辑器专业参数 → ComfyUI Wan workflow 映射。"""
from __future__ import annotations

from dataclasses import dataclass

STYLE_PRESET_TAGS: dict[str, str] = {
    "cinematic": "cinematic lighting, film grain, shallow depth of field",
    "anime": "anime style, vibrant colors, clean line art",
    "realistic": "photorealistic, natural lighting, high detail",
    "ads": "commercial advertisement style, polished lighting, product focus",
    "documentary": "documentary footage, handheld camera feel, natural color",
    "cyberpunk": "cyberpunk, neon lights, rainy night city",
    "sci-fi": "science fiction, futuristic, epic scale",
    "fantasy": "fantasy epic, magical atmosphere, dramatic lighting",
    "noir": "film noir, high contrast, moody shadows",
    "vintage": "vintage film, faded colors, film grain",
    "minimal": "minimalist, clean composition, soft lighting",
    "chinese-style": "Chinese traditional aesthetic, elegant, ink wash mood",
    "ink": "Chinese ink painting style, brush strokes, artistic",
    "pixel": "pixel art style, retro game aesthetic",
    "low-poly": "low poly 3D style, geometric shapes",
    "3d-cartoon": "3D cartoon render, stylized characters",
    "game-cg": "game cinematic CG, high quality render",
    "product-showcase": "product showcase, studio lighting, sharp focus",
    "architecture": "architectural visualization, smooth camera motion",
    "fashion": "fashion film, editorial lighting, stylish",
    "food": "food photography, appetizing, warm lighting",
    "travel": "travel vlog style, vibrant, scenic",
    "tech": "tech product launch, sleek, modern",
    "music-video": "music video style, dynamic lighting, rhythmic motion",
}

MOTION_TO_SHIFT: dict[str, float] = {
    "low": 3.0,
    "medium": 5.0,
    "high": 8.0,
}

_SIZE_TABLE: dict[tuple[str, str], tuple[int, int]] = {
    # Wan2.1-T2V-1.3B 推荐（与 workflow.json 默认一致）
    ("480p", "16:9"): (832, 480),
    ("480p", "9:16"): (480, 832),
    ("480p", "1:1"): (480, 480),
    ("480p", "21:9"): (1120, 480),
    ("720p", "16:9"): (1280, 720),
    ("720p", "9:16"): (720, 1280),
    ("720p", "1:1"): (720, 720),
    ("720p", "21:9"): (1680, 720),
    ("1080p", "16:9"): (1920, 1088),
    ("1080p", "9:16"): (1088, 1920),
    ("1080p", "1:1"): (1088, 1088),
    ("1080p", "21:9"): (2520, 1080),
    ("2k", "16:9"): (2560, 1440),
    ("2k", "9:16"): (1440, 2560),
    ("2k", "1:1"): (1440, 1440),
    ("2k", "21:9"): (3360, 1440),
    ("4k", "16:9"): (3840, 2160),
    ("4k", "9:16"): (2160, 3840),
    ("4k", "1:1"): (2160, 2160),
    ("4k", "21:9"): (5040, 2160),
}


def _align8(n: int) -> int:
    return max(64, int(round(n / 8)) * 8)


def resolution_aspect_to_size(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    res = str(resolution or "1080p").strip().lower()
    ar = str(aspect_ratio or "16:9").strip()
    if res in ("4k", "2160p"):
        res = "4k"
    elif res == "2k":
        res = "2k"
    elif res in ("480", "480p"):
        res = "480p"
    elif res in ("720", "720p"):
        res = "720p"
    elif res not in ("480p", "1080p", "2k", "4k", "720p"):
        res = "480p"
    w, h = _SIZE_TABLE.get((res, ar), _SIZE_TABLE[("480p", "16:9")])
    return _align8(w), _align8(h)


def motion_to_shift(motion: str) -> float:
    return MOTION_TO_SHIFT.get(str(motion or "medium").strip().lower(), 5.0)


def motion_to_i2v_encode(motion: str) -> tuple[float, float]:
    """图生视频：start_latent_strength（越低动作越大）, noise_aug_strength。"""
    m = str(motion or "medium").strip().lower()
    if m == "low":
        return 1.0, 0.0
    if m == "high":
        return 0.82, 0.04
    return 0.92, 0.02


def quality_adjust_steps(quality: str, steps: int) -> int:
    s = max(8, min(int(steps), 120))
    if str(quality or "standard").strip().lower() == "pro":
        return s
    return max(8, min(s, 28))


def duration_fps_to_num_frames(duration_sec: float, fps: float) -> int:
    raw = int(float(duration_sec) * float(fps)) + 1
    raw = max(5, min(raw, 10000))
    return ((raw - 1) // 4) * 4 + 1


def compose_positive_prompt(prompt: str, style_preset: str, custom_style: str) -> str:
    base = str(prompt or "").strip()
    parts = [base] if base else []
    tag = STYLE_PRESET_TAGS.get(str(style_preset or "").strip(), "")
    if tag:
        parts.append(tag)
    extra = str(custom_style or "").strip()
    if extra:
        parts.append(extra)
    return ", ".join(parts) if parts else base


@dataclass
class VideoGenParams:
    prompt: str
    negative: str = "blurry, low quality, static"
    seed: int | None = None
    duration_sec: float = 6.0
    fps: float = 24.0
    resolution: str = "480p"
    aspect_ratio: str = "16:9"
    steps: int = 28
    cfg_scale: float = 7.0
    motion: str = "medium"
    quality: str = "standard"
    style_preset: str = "cinematic"
    custom_style: str = ""
    image_base64: str | None = None

    @classmethod
    def from_request(cls, req) -> "VideoGenParams":
        img = getattr(req, "image_base64", None)
        return cls(
            prompt=req.prompt,
            negative=req.negative,
            seed=req.seed,
            duration_sec=req.duration,
            fps=req.fps,
            resolution=req.resolution,
            aspect_ratio=req.aspect_ratio,
            steps=req.steps,
            cfg_scale=req.cfg_scale,
            motion=req.motion,
            quality=req.quality,
            style_preset=req.style_preset,
            custom_style=getattr(req, "custom_style", "") or "",
            image_base64=str(img).strip() if img else None,
        )

    @property
    def is_i2v(self) -> bool:
        return bool(self.image_base64 and str(self.image_base64).strip())

    @property
    def positive_prompt(self) -> str:
        return compose_positive_prompt(self.prompt, self.style_preset, self.custom_style)

    @property
    def width_height(self) -> tuple[int, int]:
        return resolution_aspect_to_size(self.resolution, self.aspect_ratio)

    @property
    def sampler_steps(self) -> int:
        return quality_adjust_steps(self.quality, self.steps)

    @property
    def sampler_cfg(self) -> float:
        return max(1.0, min(float(self.cfg_scale), 20.0))

    @property
    def sampler_shift(self) -> float:
        return motion_to_shift(self.motion)

    @property
    def i2v_latent_strength(self) -> tuple[float, float]:
        return motion_to_i2v_encode(self.motion)
