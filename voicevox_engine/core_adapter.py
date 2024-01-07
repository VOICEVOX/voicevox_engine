import threading

import numpy as np
from numpy.typing import NDArray

from .core_wrapper import CoreWrapper, OldCoreError
from .metas.Metas import StyleId


class CoreAdapter:
    """
    コアのアダプター。
    ついでにコア内部で推論している処理をプロセスセーフにする。
    """

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self.core = core
        self.mutex = threading.Lock()

    @property
    def default_sampling_rate(self) -> int:
        return self.core.default_sampling_rate

    @property
    def speakers(self) -> str:
        """話者情報（json文字列）"""
        return self.core.metas()

    @property
    def supported_devices(self) -> str | None:
        """デバイスサポート情報（None: 情報無し）"""
        try:
            supported_devices = self.core.supported_devices()
        except OldCoreError:
            supported_devices = None
        return supported_devices

    def initialize_style_id_synthesis(
        self, style_id: StyleId, skip_reinit: bool
    ) -> None:
        """
        指定したスタイルでの音声合成を初期化する。
        何度も実行可能。未実装の場合は何もしない。
        Parameters
        ----------
        style_id : StyleId
            スタイルID
        skip_reinit : bool
            True の場合, 既に初期化済みの話者の再初期化をスキップします
        """
        try:
            with self.mutex:
                # 以下の条件のいずれかを満たす場合, 初期化を実行する
                # 1. 引数 skip_reinit が False の場合
                # 2. 話者が初期化されていない場合
                if (not skip_reinit) or (not self.core.is_model_loaded(style_id)):
                    self.core.load_model(style_id)
        except OldCoreError:
            pass  # コアが古い場合はどうしようもないので何もしない

    def is_initialized_style_id_synthesis(self, style_id: StyleId) -> bool:
        """指定したスタイルでの音声合成が初期化されているかどうかを返す"""
        try:
            return self.core.is_model_loaded(style_id)
        except OldCoreError:
            return True  # コアが古い場合はどうしようもないのでTrueを返す

    def safe_yukarin_s_forward(
        self, phoneme_list_s: NDArray[np.integer], style_id: StyleId
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            phoneme_length = self.core.yukarin_s_forward(
                length=len(phoneme_list_s),
                phoneme_list=phoneme_list_s,
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )
        return phoneme_length

    def safe_yukarin_sa_forward(
        self,
        vowel_phoneme_list: NDArray[np.integer],
        consonant_phoneme_list: NDArray[np.integer],
        start_accent_list: NDArray[np.integer],
        end_accent_list: NDArray[np.integer],
        start_accent_phrase_list: NDArray[np.integer],
        end_accent_phrase_list: NDArray[np.integer],
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            f0_list = self.core.yukarin_sa_forward(
                length=vowel_phoneme_list.shape[0],
                vowel_phoneme_list=vowel_phoneme_list[np.newaxis],
                consonant_phoneme_list=consonant_phoneme_list[np.newaxis],
                start_accent_list=start_accent_list[np.newaxis],
                end_accent_list=end_accent_list[np.newaxis],
                start_accent_phrase_list=start_accent_phrase_list[np.newaxis],
                end_accent_phrase_list=end_accent_phrase_list[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )[0]
        return f0_list

    def safe_decode_forward(
        self,
        phoneme: NDArray[np.floating],
        f0: NDArray[np.floating],
        style_id: StyleId,
    ) -> tuple[NDArray[np.float32], int]:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            wave = self.core.decode_forward(
                length=phoneme.shape[0],
                phoneme_size=phoneme.shape[1],
                f0=f0[:, np.newaxis],
                phoneme=phoneme,
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )
        sr_wave = self.default_sampling_rate
        return wave, sr_wave
