import os
from typing import Dict, Optional

from model.env_config_model import env_config_model


class AiConfigLogic:
    def __init__(self, config_model):
        self.config_model = config_model

    def get_config(self) -> Dict[str, object]:
        config = self.config_model.get_ai_config()
        return self._build_response(config)

    def update_config(self, payload: Dict[str, object], runtime_config) -> Dict[str, object]:
        if payload is None:
            raise ValueError("请求体不能为空")

        current_config = self.config_model.get_ai_config()
        text_model = self._validate_model(payload.get("text_model"), "文本模型")
        vision_model = self._validate_model(payload.get("vision_model"), "视觉模型")
        api_key = self._normalize_api_key(payload.get("api_key"), current_config["api_key"])

        saved_config = self.config_model.update_ai_config(
            text_model=text_model,
            vision_model=vision_model,
            api_key=api_key,
        )
        self._refresh_runtime_config(runtime_config, saved_config)
        return self._build_response(saved_config)

    def _validate_model(self, value: object, field_name: str) -> str:
        if value is None:
            raise ValueError(f"{field_name}不能为空")
        if not isinstance(value, str):
            raise ValueError(f"{field_name}格式不合法")

        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError(f"{field_name}不能为空")
        if len(cleaned_value) > 100:
            raise ValueError(f"{field_name}长度不能超过100个字符")
        if any(char in cleaned_value for char in ("\r", "\n")):
            raise ValueError(f"{field_name}不能包含换行")
        return cleaned_value

    def _normalize_api_key(self, new_value: object, current_value: str) -> Optional[str]:
        if new_value is None:
            return None
        if not isinstance(new_value, str):
            raise ValueError("API Key 格式不合法")

        cleaned_value = new_value.strip()
        if not cleaned_value:
            return None
        if len(cleaned_value) > 256:
            raise ValueError("API Key 长度不能超过256个字符")
        if any(char in cleaned_value for char in ("\r", "\n")):
            raise ValueError("API Key 不能包含换行")

        if cleaned_value == current_value:
            return None
        return cleaned_value

    def _refresh_runtime_config(self, runtime_config, saved_config: Dict[str, str]) -> None:
        runtime_config["ALIYUN_MODEL"] = saved_config["text_model"]
        runtime_config["ALIYUN_VL_MODEL"] = saved_config["vision_model"]
        runtime_config["ALIYUN_API_KEY"] = saved_config["api_key"]

        os.environ["ALIYUN_MODEL"] = saved_config["text_model"]
        os.environ["ALIYUN_VL_MODEL"] = saved_config["vision_model"]
        os.environ["ALIYUN_API_KEY"] = saved_config["api_key"]

    def _build_response(self, config: Dict[str, str]) -> Dict[str, object]:
        api_key = config["api_key"]
        return {
            "text_model": config["text_model"],
            "vision_model": config["vision_model"],
            "has_api_key": bool(api_key),
            "api_key_masked": self._mask_api_key(api_key),
        }

    def _mask_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


ai_config_logic = AiConfigLogic(env_config_model)
