#!/usr/bin/env python3
"""
启动视频 HTTP 服务。直接运行即可，自动使用本目录下的 ComfyUI。

  python run.py
  python run.py -e F:/ComfyUI/video-engine -m D:/models   # 仅高级用户
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def _check_models(s) -> int:
    """缺模型时打印路径并返回非 0 退出码。"""
    from paths import _engine_candidates, wan_models_complete
    from engine_paths import resolve_engine

    missing = []
    for label, path in (
        ("扩散模型", s.models.gguf_file),
        ("文本编码器", s.models.t5_file),
        ("VAE", s.models.vae_file),
    ):
        if not path.is_file() or path.stat().st_size <= 0:
            missing.append(f"  · {label}：{path}")
    if not missing:
        return 0

    print("缺少模型文件，请按 MODELS.md 放到 ComfyUI/models 下：", file=sys.stderr)
    for line in missing:
        print(line, file=sys.stderr)

    # 提示：模型若在其它已检测到的引擎目录里，说明当前未指到该目录
    alts: list[str] = []
    for er in _engine_candidates(s.package_root):
        if er.resolve() == s.engine_root.resolve():
            continue
        _, _, models_dir = resolve_engine(er)
        if wan_models_complete(models_dir):
            alts.append(str(models_dir))
    if alts:
        print("检测到模型已在下列目录（将自动使用需更新程序；或在本目录 config.env 写 MODELS_ROOT）：", file=sys.stderr)
        for a in alts:
            print(f"  · {a}", file=sys.stderr)
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from app_paths import install_root

    here = install_root()
    p = argparse.ArgumentParser(description="视频 HTTP 服务")
    p.add_argument(
        "-p", "--package",
        default=str(here),
        help="API 目录（默认本文件夹）",
    )
    p.add_argument(
        "-e", "--engine",
        default="",
        help="引擎目录（可省略，自动找同级 video-engine）",
    )
    p.add_argument(
        "-m", "--models",
        default="",
        help="模型根目录（可选；默认用引擎下 models）",
    )
    p.add_argument(
        "-o", "--output",
        default="",
        help="生成视频输出目录（可选）",
    )
    p.add_argument(
        "-c", "--config",
        default="",
        help="额外 config.env 文件（可选）",
    )
    p.add_argument("--api-host", default="", help="API 监听地址，默认 0.0.0.0")
    p.add_argument("--api-port", type=int, default=0, help="API 端口，默认 8080")
    p.add_argument("--comfy-host", default="", help="ComfyUI 地址，默认 127.0.0.1")
    p.add_argument("--comfy-port", type=int, default=0, help="ComfyUI 端口，默认 8188")
    p.add_argument(
        "--no-start-engine",
        action="store_true",
        help="不自动启动引擎（引擎已在跑时用）",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from config_loader import configure
    from paths import detect_engine

    pkg_path = Path(args.package).resolve()
    engine = args.engine.strip() if args.engine else ""
    if not engine:
        try:
            detected = detect_engine(pkg_path)
            # 单目录布局：引擎即本包目录（内含 ComfyUI）
            engine = str(detected)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 1

    try:
        s = configure(
            package_dir=args.package,
            engine_dir=engine,
            models_dir=args.models or None,
            output_dir=args.output or None,
            config_file=args.config or None,
            service_host=args.api_host or None,
            service_port=args.api_port or None,
            comfy_host=args.comfy_host or None,
            comfy_port=args.comfy_port or None,
            auto_start_engine=False if args.no_start_engine else None,
        )
    except (RuntimeError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 1

    rc = _check_models(s)
    if rc:
        return rc

    host_show = "127.0.0.1" if s.service_host in ("0.0.0.0", "::") else s.service_host
    print("—— 视频服务已就绪 ——")
    print(f"引擎：{s.engine_root}")
    print(f"模型：{s.models.gguf_file.parent.parent}")
    print(f"调用：http://{host_show}:{s.service_port}/v1/video")
    print('示例：{"prompt":"一只猫在海边"}')
    print(f"（内部 ComfyUI {s.comfy_url}，自动启动={s.auto_start_engine}）")

    uvicorn.run(
        "server:create_app",
        factory=True,
        host=s.service_host,
        port=s.service_port,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
