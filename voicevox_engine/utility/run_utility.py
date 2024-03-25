import os
import warnings


def decide_boolean_from_env(env_name: str) -> bool:
    """
    環境変数からbool値を返す。

    * 環境変数が"1"ならTrueを返す
    * 環境変数が"0"か空白か存在しないならFalseを返す
    * それ以外はwarningを出してFalseを返す
    """
    env = os.getenv(env_name, default="")
    if env == "1":
        return True
    elif env == "" or env == "0":
        return False
    else:
        warnings.warn(
            f"Invalid environment variable value: {env_name}={env}",
            stacklevel=1,
        )
        return False
