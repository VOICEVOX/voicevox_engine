"""バリデーション・ダンプに関する utility"""

from typing import Any, Callable, TypeVar

from pydantic import TypeAdapter


T = TypeVar("T")

def generate_obj_validator(type: type[T]) -> Callable[[Any], T]:
    x_adapter = TypeAdapter(type)

    def validate_obj_as_x(obj: Any) -> T:
        validated: T = x_adapter.validate_python(obj)
        return validated

    return validate_obj_as_x


S = TypeVar("S")

def generate_obj_dumper(type: type[S]) -> Callable[[S], Any]:
    x_adapter = TypeAdapter(type)

    def dump_x_as_obj(x: S) -> Any:
        return x_adapter.dump_python(x)

    return dump_x_as_obj


U = TypeVar("U")

def generate_bytes_validator(type: type[U]) -> Callable[[bytes], U]:
    x_adapter = TypeAdapter(type)

    def validate_bytes_as_x(byte: bytes) -> U:
        validated: U = x_adapter.validate_json(byte)
        return validated

    return validate_bytes_as_x


V = TypeVar("V")

def generate_bytes_dumper(type: type[V]) -> Callable[[V], bytes]:
    x_adapter = TypeAdapter(type)

    def dump_x_as_bytes(x: V) -> bytes:
        return x_adapter.dump_json(x)

    return dump_x_as_bytes
