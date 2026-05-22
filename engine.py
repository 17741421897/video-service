"""Hidden ComfyUI engine: subprocess lifecycle (not exposed to API users)."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from engine_paths import resolve_engine


class ComfyEngine:
    def __init__(
        self,
        engine_root: Path,
        host: str = "127.0.0.1",
        port: int = 8188,
        extra_model_paths_yaml: Path | None = None,
    ) -> None:
        self.engine_root = engine_root.resolve()
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.extra_model_paths_yaml = extra_model_paths_yaml
        self._proc: subprocess.Popen | None = None

    def _extra_args(self) -> list[str]:
        if self.extra_model_paths_yaml and self.extra_model_paths_yaml.is_file():
            return ["--extra-model-paths-config", str(self.extra_model_paths_yaml)]
        return []

    @property
    def comfy_dir(self) -> Path:
        return resolve_engine(self.engine_root)[1]

    def _python(self) -> str:
        env_sh = self.engine_root / "env_common.sh"
        if sys.platform != "win32" and env_sh.is_file():
            return "conda-run"  # resolved via shell in start script
        bat = self.engine_root / "env_common.bat"
        if bat.is_file():
            return os.environ.get("COMFY_PYTHON", sys.executable)
        return sys.executable

    def is_up(self, timeout: float = 2.0) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/system_stats", timeout=timeout) as r:
                return r.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def wait_up(self, deadline_sec: float = 300.0, poll: float = 2.0) -> None:
        end = time.time() + deadline_sec
        while time.time() < end:
            if self.is_up():
                return
            if self._proc and self._proc.poll() is not None:
                raise RuntimeError(f"ComfyUI exited with code {self._proc.returncode}")
            time.sleep(poll)
        raise TimeoutError(f"ComfyUI not ready at {self.base_url}")

    def start(self) -> None:
        if self.is_up():
            return
        main_py = self.comfy_dir / "main.py"
        if not main_py.is_file():
            raise FileNotFoundError(f"Engine not found: {main_py}. Set ENGINE_ROOT in config.env")

        if sys.platform == "win32":
            py = os.environ.get("COMFY_PYTHON", sys.executable)
            cmd = [
                py,
                str(main_py),
                "--listen",
                self.host,
                "--port",
                str(self.port),
                "--disable-auto-launch",
                *self._extra_args(),
            ]
            cwd = str(self.comfy_dir)
            self._proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            start_api = self.engine_root / "start_api.sh"
            if start_api.is_file() and not self._extra_args():
                env = os.environ.copy()
                env["COMFY_LISTEN"] = self.host
                env["COMFY_PORT"] = str(self.port)
                self._proc = subprocess.Popen(
                    ["bash", str(start_api)],
                    cwd=str(self.engine_root),
                    env=env,
                    start_new_session=True,
                )
            else:
                py = os.environ.get("COMFY_PYTHON", sys.executable)
                self._proc = subprocess.Popen(
                    [
                        py,
                        str(main_py),
                        "--listen",
                        self.host,
                        "--port",
                        str(self.port),
                        "--disable-auto-launch",
                        *self._extra_args(),
                    ],
                    cwd=str(self.comfy_dir),
                    start_new_session=True,
                )
        self.wait_up()

    def stop(self) -> None:
        if not self._proc:
            return
        try:
            if sys.platform == "win32":
                self._proc.terminate()
            else:
                os.killpg(self._proc.pid, signal.SIGTERM)
            self._proc.wait(timeout=30)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
        self._proc = None
