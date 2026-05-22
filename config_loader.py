"""Load settings: config file + CLI overrides (package / engine / models dirs)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app_paths import install_root
from engine_paths import resolve_engine
from models_config import ModelPaths, load_model_paths

_DEFAULT_ROOT = install_root()
_instance: Settings | None = None


def package_root() -> Path:
    root = os.environ.get("VIDEO_PACKAGE_ROOT") or os.environ.get("WAN_PACKAGE_ROOT", "")
    return Path(root or _DEFAULT_ROOT).resolve()


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if override:
            os.environ[key] = val
        else:
            os.environ.setdefault(key, val)


@dataclass
class Settings:
    package_root: Path
    engine_root: Path
    comfy_host: str
    comfy_port: int
    service_host: str
    service_port: int
    auto_start_engine: bool
    workflow_path: Path
    workflow_i2v_path: Path
    output_dir: Path
    models: ModelPaths

    @property
    def comfy_url(self) -> str:
        return f"http://{self.comfy_host}:{self.comfy_port}"


def configure(
    *,
    package_dir: str | Path | None = None,
    engine_dir: str | Path | None = None,
    models_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    config_file: str | Path | None = None,
    service_host: str | None = None,
    service_port: int | None = None,
    comfy_host: str | None = None,
    comfy_port: int | None = None,
    auto_start_engine: bool | None = None,
) -> Settings:
    """Apply startup paths (CLI). Call once before starting uvicorn."""
    global _instance

    root = Path(package_dir).resolve() if package_dir else _DEFAULT_ROOT
    os.environ["VIDEO_PACKAGE_ROOT"] = str(root)
    os.environ["WAN_PACKAGE_ROOT"] = str(root)  # 兼容旧配置

    _load_env_file(root / "config.env")
    if config_file:
        _load_env_file(Path(config_file).expanduser().resolve(), override=True)

    overrides: dict[str, str] = {}
    if engine_dir is not None:
        overrides["ENGINE_ROOT"] = str(Path(engine_dir).expanduser().resolve())
    if models_dir is not None:
        overrides["MODELS_ROOT"] = str(Path(models_dir).expanduser().resolve())
    if output_dir is not None:
        out = str(Path(output_dir).expanduser().resolve())
        overrides["VIDEO_OUTPUT_DIR"] = out
        overrides["WAN_OUTPUT_DIR"] = out
    if service_host is not None:
        overrides["SERVICE_HOST"] = service_host
    if service_port is not None:
        overrides["SERVICE_PORT"] = str(service_port)
    if comfy_host is not None:
        overrides["COMFY_HOST"] = comfy_host
    if comfy_port is not None:
        overrides["COMFY_PORT"] = str(comfy_port)
    if auto_start_engine is not None:
        overrides["AUTO_START_ENGINE"] = "1" if auto_start_engine else "0"

    for key, val in overrides.items():
        os.environ[key] = val

    engine = os.environ.get("ENGINE_ROOT", "").strip()
    if not engine:
        from paths import detect_engine

        engine = str(detect_engine(root))
        os.environ["ENGINE_ROOT"] = engine

    engine_root = Path(engine).expanduser().resolve()
    resolve_engine(engine_root)

    out = os.environ.get("WAN_OUTPUT_DIR", "").strip()
    out_path = Path(out).resolve() if out else root / "output"

    _instance = Settings(
        package_root=root,
        engine_root=engine_root,
        comfy_host=os.environ.get("COMFY_HOST", "127.0.0.1"),
        comfy_port=int(os.environ.get("COMFY_PORT", "8188")),
        service_host=os.environ.get("SERVICE_HOST", "0.0.0.0"),
        service_port=int(os.environ.get("SERVICE_PORT", "8080")),
        auto_start_engine=os.environ.get("AUTO_START_ENGINE", "1") not in ("0", "false", "False"),
        workflow_path=root / "workflow.json",
        workflow_i2v_path=root / "workflow_i2v.json",
        output_dir=out_path,
        models=load_model_paths(engine_root, root),
    )
    return _instance


def get_settings() -> Settings:
    global _instance
    if _instance is not None:
        return _instance
    os.environ.setdefault("VIDEO_PACKAGE_ROOT", str(_DEFAULT_ROOT))
    _load_env_file(_DEFAULT_ROOT / "config.env")
    _load_env_file(_DEFAULT_ROOT / "config.example.env")
    return configure(engine_dir=os.environ.get("ENGINE_ROOT") or None)
