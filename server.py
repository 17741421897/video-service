#!/usr/bin/env python3
"""视频 HTTP API。"""
from __future__ import annotations

import shutil
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from client import generate as gen_video
from gen_params import VideoGenParams
from config_loader import Settings, get_settings
from engine import ComfyEngine


class VideoRequest(BaseModel):
    """与贤紫代码编辑器视频模式专业参数一一对应。"""
    prompt: str = Field(..., min_length=1)
    negative: str = "blurry, low quality, static"
    seed: int | None = None
    duration: float = Field(6.0, ge=1.0, le=30.0)
    fps: float = Field(24.0, ge=8.0, le=60.0)
    resolution: str = Field("480p", description="480p(推荐) | 720p | 1080p | 2k | 4k")
    aspect_ratio: str = Field("16:9", description="16:9 | 9:16 | 1:1 | 21:9")
    steps: int = Field(28, ge=8, le=120)
    cfg_scale: float = Field(7.0, ge=1.0, le=20.0)
    motion: str = Field("medium", description="low | medium | high → sampler shift")
    quality: str = Field("standard", description="standard | pro")
    style_preset: str = Field("cinematic")
    custom_style: str = Field("")


class VideoI2VRequest(VideoRequest):
    """图生视频：须上传参考图 Base64（可带 data:image/... 前缀）。"""
    image_base64: str = Field(..., min_length=16)


class VideoResponse(BaseModel):
    job_id: str
    path: str
    download_url: str


def create_app() -> FastAPI:
    settings = get_settings()
    engine = ComfyEngine(
        settings.engine_root,
        settings.comfy_host,
        settings.comfy_port,
        settings.models.extra_model_paths_yaml,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.auto_start_engine:
            engine.start()
        yield
        engine.stop()

    app = FastAPI(
        title="Video API",
        version="1.0.0",
        lifespan=lifespan,
    )
    # 贤紫代码编辑器等本地 Web/Electron 页面跨域调用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.engine = engine

    def _public_base_url() -> str:
        host = settings.service_host
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        return f"http://{host}:{settings.service_port}"

    @app.get("/health")
    def health():
        m = settings.models
        return {
            "status": "ok" if engine.is_up() else "engine_down",
            "package": str(settings.package_root),
            "engine_root": str(settings.engine_root),
            "engine": settings.comfy_url,
            "service": f"http://{settings.service_host}:{settings.service_port}",
            "models": {
                "gguf": str(m.gguf_file),
                "t5": str(m.t5_file),
                "vae": str(m.vae_file),
            },
        }

    def _do_create_video(req: VideoRequest) -> VideoResponse:
        if not engine.is_up():
            try:
                engine.start()
            except Exception as e:
                raise HTTPException(503, f"engine not available: {e}") from e

        job_id = str(uuid.uuid4())
        out_dir = settings.output_dir / job_id
        try:
            params = VideoGenParams.from_request(req)
            path = gen_video(
                comfy_url=settings.comfy_url,
                workflow_path=settings.workflow_path,
                workflow_i2v_path=settings.workflow_i2v_path,
                engine_root=settings.engine_root,
                params=params,
                job_id=job_id,
                out_dir=out_dir,
                models=settings.models,
            )
        except TimeoutError as e:
            raise HTTPException(504, str(e)) from e
        except Exception as e:
            raise HTTPException(500, str(e)) from e

        return VideoResponse(
            job_id=job_id,
            path=str(path),
            download_url=f"{_public_base_url()}/v1/video/{job_id}/file",
        )

    @app.post("/v1/video", response_model=VideoResponse)
    def create_video_v1(req: VideoRequest):
        return _do_create_video(req)

    @app.post("/video/t2v", response_model=VideoResponse)
    def create_video_t2v(req: VideoRequest):
        """兼容贤紫编辑器等「统一底座 + /video/t2v」用法。"""
        return _do_create_video(req)

    def _do_create_video_i2v(req: VideoI2VRequest) -> VideoResponse:
        if not engine.is_up():
            try:
                engine.start()
            except Exception as e:
                raise HTTPException(503, f"engine not available: {e}") from e
        job_id = str(uuid.uuid4())
        out_dir = settings.output_dir / job_id
        try:
            params = VideoGenParams.from_request(req)
            path = gen_video(
                comfy_url=settings.comfy_url,
                workflow_path=settings.workflow_path,
                workflow_i2v_path=settings.workflow_i2v_path,
                engine_root=settings.engine_root,
                params=params,
                job_id=job_id,
                out_dir=out_dir,
                models=settings.models,
            )
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        except TimeoutError as e:
            raise HTTPException(504, str(e)) from e
        except FileNotFoundError as e:
            raise HTTPException(500, str(e)) from e
        except Exception as e:
            raise HTTPException(500, str(e)) from e
        return VideoResponse(
            job_id=job_id,
            path=str(path),
            download_url=f"{_public_base_url()}/v1/video/{job_id}/file",
        )

    @app.post("/v1/video/i2v", response_model=VideoResponse)
    def create_video_i2v_v1(req: VideoI2VRequest):
        return _do_create_video_i2v(req)

    @app.post("/video/i2v", response_model=VideoResponse)
    def create_video_i2v(req: VideoI2VRequest):
        """贤紫编辑器图生视频默认路由。"""
        return _do_create_video_i2v(req)

    @app.get("/v1/video/{job_id}/file")
    def download_video(job_id: str):
        folder = settings.output_dir / job_id
        if not folder.is_dir():
            raise HTTPException(404, "job not found")
        files = [f for f in folder.iterdir() if f.is_file()]
        if not files:
            raise HTTPException(404, "no video file")
        return FileResponse(files[0], media_type="video/mp4", filename=files[0].name)

    @app.delete("/v1/video/{job_id}")
    def delete_job(job_id: str):
        folder = settings.output_dir / job_id
        if folder.is_dir():
            shutil.rmtree(folder)
        return {"deleted": job_id}

    return app
