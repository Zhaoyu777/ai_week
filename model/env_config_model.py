import os
import tempfile
import threading
import time
from typing import Dict, Optional

from dotenv import dotenv_values


class EnvConfigModel:
    """Persist AI-related configuration in the .env file."""

    _thread_lock = threading.Lock()

    def __init__(self, env_path: Optional[str] = None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_env_path = os.getenv("APP_ENV_FILE", os.path.join(project_root, ".env"))
        self.env_path = env_path or default_env_path
        self.lock_path = f"{self.env_path}.lock"
        self.ai_keys = ("ALIYUN_API_KEY", "ALIYUN_MODEL", "ALIYUN_VL_MODEL")

    def get_ai_config(self) -> Dict[str, str]:
        values = dotenv_values(self.env_path)
        return {
            "api_key": (values.get("ALIYUN_API_KEY") or "").strip(),
            "text_model": (values.get("ALIYUN_MODEL") or "").strip(),
            "vision_model": (values.get("ALIYUN_VL_MODEL") or "").strip(),
        }

    def update_ai_config(
        self,
        *,
        text_model: str,
        vision_model: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, str]:
        updates = {
            "ALIYUN_MODEL": text_model,
            "ALIYUN_VL_MODEL": vision_model,
        }
        if api_key is not None:
            updates["ALIYUN_API_KEY"] = api_key

        with self._thread_lock:
            self._acquire_file_lock()
            try:
                existing_lines = self._read_env_lines()
                merged_content = self._merge_lines(existing_lines, updates)
                self._atomic_write(merged_content)
            finally:
                self._release_file_lock()

        return self.get_ai_config()

    def _read_env_lines(self):
        if not os.path.exists(self.env_path):
            return []

        with open(self.env_path, "r", encoding="utf-8") as env_file:
            return env_file.readlines()

    def _merge_lines(self, lines, updates: Dict[str, str]) -> str:
        merged_lines = list(lines)
        pending_keys = list(updates.keys())

        for index, line in enumerate(merged_lines):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#") or "=" not in line:
                continue

            key, _, _ = line.partition("=")
            env_key = key.strip()
            if env_key in updates:
                merged_lines[index] = f"{env_key}={updates[env_key]}\n"
                if env_key in pending_keys:
                    pending_keys.remove(env_key)

        if merged_lines and not merged_lines[-1].endswith("\n"):
            merged_lines[-1] = merged_lines[-1] + "\n"

        for env_key in self.ai_keys:
            if env_key in pending_keys:
                merged_lines.append(f"{env_key}={updates[env_key]}\n")

        return "".join(merged_lines)

    def _atomic_write(self, content: str) -> None:
        env_dir = os.path.dirname(self.env_path) or "."
        os.makedirs(env_dir, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(prefix=".env.", dir=env_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temp_file:
                temp_file.write(content)
            os.replace(temp_path, self.env_path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def _acquire_file_lock(self, timeout_seconds: float = 5.0, sleep_seconds: float = 0.1) -> None:
        started_at = time.monotonic()

        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                return
            except FileExistsError:
                if time.monotonic() - started_at >= timeout_seconds:
                    raise TimeoutError("配置文件正在被其他请求更新，请稍后重试")
                time.sleep(sleep_seconds)

    def _release_file_lock(self) -> None:
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)


env_config_model = EnvConfigModel()
