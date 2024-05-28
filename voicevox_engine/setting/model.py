"""
エンジン設定機能に関して API と ENGINE 内部実装が共有するモデル
「API と ENGINE 内部実装が共有するモデル」については `voicevox_engine/model.py` の module docstring を確認すること。
"""

from enum import Enum


class CorsPolicyMode(str, Enum):
    """
    CORSの許可モード
    """

    all = "all"  # 全てのオリジンからのリクエストを許可
    localapps = "localapps"  # ローカルアプリケーションからのリクエストを許可
