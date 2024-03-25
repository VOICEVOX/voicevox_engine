import hashlib
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


def hash_long_string(value: Any) -> Any:
    """文字数が1000文字を超えるものはハッシュ化する"""

    def to_hash(value: str) -> str:
        return "MD5:" + hashlib.md5(value.encode()).hexdigest()

    if isinstance(value, str):
        return value if len(value) <= 1000 else to_hash(value)
    elif isinstance(value, list):
        return [hash_long_string(v) for v in value]
    elif isinstance(value, dict):
        return {k: hash_long_string(v) for k, v in value.items()}
    else:
        return value
