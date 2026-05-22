"""Video generation client (talks to ComfyUI /prompt only)."""
from __future__ import annotations

import json
import random
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

from engine_paths import resolve_engine
from gen_params import VideoGenParams, duration_fps_to_num_frames, motion_to_i2v_encode
from image_io import decode_image_base64, write_comfy_input_image


def _http_json(url: str, data: dict | None = None, timeout: int = 300) -> dict:
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _patch_workflow(
    prompt: dict,
    params: VideoGenParams,
    seed: int,
    *,
    load_image_name: str | None = None,
    models=None,
) -> dict:
    num_frames = duration_fps_to_num_frames(params.duration_sec, params.fps)
    width, height = params.width_height
    positive = params.positive_prompt
    negative = params.negative
    latent_strength, noise_aug = motion_to_i2v_encode(params.motion)

    for _nid, n in prompt.items():
        ct = n.get("class_type")
        ins = n.setdefault("inputs", {})
        if ct == "WanVideoTextEncode":
            ins["positive_prompt"] = positive
            ins["negative_prompt"] = negative
        elif ct == "WanVideoEmptyEmbeds":
            ins["num_frames"] = num_frames
            ins["width"] = width
            ins["height"] = height
        elif ct == "WanVideoImageToVideoEncode":
            ins["num_frames"] = num_frames
            ins["width"] = width
            ins["height"] = height
            ins["start_latent_strength"] = latent_strength
            ins["noise_aug_strength"] = noise_aug
        elif ct == "LoadImage" and load_image_name:
            ins["image"] = load_image_name
        elif ct == "CreateVideo":
            ins["fps"] = float(params.fps)
        elif ct == "WanVideoSampler":
            ins["seed"] = seed
            ins["steps"] = params.sampler_steps
            ins["cfg"] = params.sampler_cfg
            ins["shift"] = params.sampler_shift
    if models is not None:
        models.patch_workflow(prompt)
    return prompt


def generate(
    *,
    comfy_url: str,
    workflow_path: Path,
    workflow_i2v_path: Path,
    engine_root: Path,
    params: VideoGenParams,
    job_id: str,
    out_dir: Path,
    timeout: int = 7200,
    models=None,
) -> Path:
    _, comfy_dir, _ = resolve_engine(engine_root)

    if params.is_i2v:
        wf_path = workflow_i2v_path
        if not wf_path.is_file():
            raise FileNotFoundError(f"缺少图生视频工作流: {wf_path}")
        raw = decode_image_base64(params.image_base64 or "")
        load_name = write_comfy_input_image(raw, comfy_dir, job_id)
    else:
        wf_path = workflow_path
        load_name = None

    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    use_seed = params.seed if params.seed is not None else random.randint(0, 2**32 - 1)
    workflow = _patch_workflow(
        workflow, params, use_seed, load_image_name=load_name, models=models
    )

    client_id = str(uuid.uuid4())
    prompt_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id, "prompt_id": prompt_id}
    r = _http_json(f"{comfy_url.rstrip('/')}/prompt", payload)
    if "error" in r:
        raise RuntimeError(str(r))

    deadline = time.time() + timeout
    history = None
    while time.time() < deadline:
        try:
            hist = _http_json(f"{comfy_url.rstrip('/')}/history/{prompt_id}", timeout=60)
            if prompt_id in hist:
                history = hist[prompt_id]
                break
        except urllib.error.HTTPError:
            pass
        time.sleep(2.0)
    if history is None:
        raise TimeoutError("generation timed out")

    out_dir.mkdir(parents=True, exist_ok=True)
    for _node_id, node_out in history.get("outputs", {}).items():
        for key in ("videos", "gifs", "images"):
            if key not in node_out:
                continue
            for item in node_out[key]:
                params_q = urllib.parse.urlencode(
                    {
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    }
                )
                url = f"{comfy_url.rstrip('/')}/view?{params_q}"
                with urllib.request.urlopen(url, timeout=120) as resp:
                    data = resp.read()
                path = out_dir / item["filename"]
                path.write_bytes(data)
                return path
    raise RuntimeError("no video in output")
