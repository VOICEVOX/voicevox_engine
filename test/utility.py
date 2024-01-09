import json
from typing import Any

from pydantic.json import pydantic_encoder


def round_floats(value: Any, round_value: int) -> Any:
    """floatの小数点以下を再帰的に丸める"""
    if isinstance(value, float):
        return round(value, round_value)
    elif isinstance(value, list):
        return [round_floats(v, round_value) for v in value]
    elif isinstance(value, dict):
        return {k: round_floats(v, round_value) for k, v in value.items()}
    else:
        return value


def pydantic_to_native_type(value: Any) -> Any:
    """pydanticの型をnativeな型に変換する"""
    return json.loads(json.dumps(value, default=pydantic_encoder))
