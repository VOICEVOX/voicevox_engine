"""VOICEVOX CORE のアダプター"""

import json
import threading
from dataclasses import dataclass
from typing import Any, Literal, NewType

import numpy as np
from numpy.typing import NDArray
from pydantic import TypeAdapter

from ..metas.Metas import StyleId
from .core_wrapper import CoreWrapper, OldCoreError

CoreStyleId = NewType("CoreStyleId", int)
CoreStyleType = Literal["talk", "singing_teacher", "frame_decode", "sing"]


@dataclass(frozen=True)
class CoreCharacterStyle:
    """コアに含まれるキャラクターのスタイル情報"""

    name: str
    id: CoreStyleId
    type: CoreStyleType | None = "talk"


@dataclass(frozen=True)
class CoreCharacter:
    """コアに含まれるキャラクター情報"""

    name: str
    speaker_uuid: str
    styles: list[CoreCharacterStyle]
    version: str  # キャラクターのバージョン


_core_character_adapter = TypeAdapter(CoreCharacter)


@dataclass(frozen=True)
class DeviceSupport:
    """音声ライブラリのデバイス利用可否"""

    cpu: bool
    cuda: bool  # CUDA (Nvidia GPU)
    dml: bool  # DirectML (Nvidia GPU/Radeon GPU等)


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
    def characters(self) -> list[CoreCharacter]:
        """キャラクター情報"""
        metas: list[Any] = json.loads(self.core.metas())
        return list(map(_core_character_adapter.validate_python, metas))

    @property
    def supported_devices(self) -> DeviceSupport | None:
        """デバイスサポート情報（None: 情報無し）"""
        try:
            supported_devices = json.loads(self.core.supported_devices())
            assert isinstance(supported_devices, dict)
            device_support = DeviceSupport(
                cpu=supported_devices["cpu"],
                cuda=supported_devices["cuda"],
                dml=supported_devices["dml"],
            )
        except OldCoreError:
            device_support = None
        return device_support

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
            True の場合, 既に初期化済みのキャラクターの再初期化をスキップします
        """
        try:
            with self.mutex:
                # 以下の条件のいずれかを満たす場合, 初期化を実行する
                # 1. 引数 skip_reinit が False の場合
                # 2. キャラクターが初期化されていない場合
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
        self, phoneme_list_s: NDArray[np.int64], style_id: StyleId
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「コア仕様に従う無音付加」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)

        # 前後無音を付加する（詳細: voicevox_engine#924）
        phoneme_list_s = np.r_[0, phoneme_list_s, 0]

        with self.mutex:
            phoneme_length = self.core.yukarin_s_forward(
                length=len(phoneme_list_s),
                phoneme_list=phoneme_list_s,
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )

        # 前後無音に相当する領域を破棄する
        phoneme_length = phoneme_length[1:-1]

        return phoneme_length

    def safe_yukarin_sa_forward(
        self,
        vowel_phoneme_list: NDArray[np.int64],
        consonant_phoneme_list: NDArray[np.int64],
        start_accent_list: NDArray[np.int64],
        end_accent_list: NDArray[np.int64],
        start_accent_phrase_list: NDArray[np.int64],
        end_accent_phrase_list: NDArray[np.int64],
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「コア仕様に従う無音付加」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)

        # 前後無音を付加する（詳細: voicevox_engine#924）
        vowel_phoneme_list = np.r_[0, vowel_phoneme_list, 0]
        consonant_phoneme_list = np.r_[-1, consonant_phoneme_list, -1]
        start_accent_list = np.r_[0, start_accent_list, 0]
        end_accent_list = np.r_[0, end_accent_list, 0]
        start_accent_phrase_list = np.r_[0, start_accent_phrase_list, 0]
        end_accent_phrase_list = np.r_[0, end_accent_phrase_list, 0]

        with self.mutex:
            f0_list: NDArray[np.float32] = self.core.yukarin_sa_forward(
                length=vowel_phoneme_list.shape[0],
                vowel_phoneme_list=vowel_phoneme_list[np.newaxis],
                consonant_phoneme_list=consonant_phoneme_list[np.newaxis],
                start_accent_list=start_accent_list[np.newaxis],
                end_accent_list=end_accent_list[np.newaxis],
                start_accent_phrase_list=start_accent_phrase_list[np.newaxis],
                end_accent_phrase_list=end_accent_phrase_list[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )[0]

        # 前後無音に相当する領域を破棄する
        f0_list = f0_list[1:-1]

        return f0_list

    def safe_decode_forward(
        self,
        phoneme: NDArray[np.float32],
        f0: NDArray[np.float32],
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

    def safe_predict_sing_consonant_length_forward(
        self,
        consonant: NDArray[np.int64],
        vowel: NDArray[np.int64],
        note_duration: NDArray[np.int64],
        style_id: StyleId,
    ) -> NDArray[np.int64]:
        # 「指定スタイルを初期化」「mutexによる安全性」「コア仕様に従う無音付加」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)

        with self.mutex:
            consonant_length = self.core.predict_sing_consonant_length_forward(
                length=consonant.shape[0],
                consonant=consonant[np.newaxis],
                vowel=vowel[np.newaxis],
                note_duration=note_duration[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )

        return consonant_length

    def safe_predict_sing_f0_forward(
        self,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「コア仕様に従う無音付加」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)

        with self.mutex:
            f0 = self.core.predict_sing_f0_forward(
                length=phoneme.shape[0],
                phoneme=phoneme[np.newaxis],
                note=note[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )

        return f0

    def safe_predict_sing_volume_forward(
        self,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        f0: NDArray[np.float32],
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        # 「指定スタイルを初期化」「mutexによる安全性」「コア仕様に従う無音付加」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)

        with self.mutex:
            volume = self.core.predict_sing_volume_forward(
                length=phoneme.shape[0],
                phoneme=phoneme[np.newaxis],
                note=note[np.newaxis],
                f0=f0[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )

        return volume

    def safe_sf_decode_forward(
        self,
        phoneme: NDArray[np.int64],
        f0: NDArray[np.float32],
        volume: NDArray[np.float32],
        style_id: StyleId,
    ) -> tuple[NDArray[np.float32], int]:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            wave = self.core.sf_decode_forward(
                length=phoneme.shape[0],
                phoneme=phoneme[np.newaxis],
                f0=f0[np.newaxis],
                volume=volume[np.newaxis],
                style_id=np.array(style_id, dtype=np.int64).reshape(-1),
            )
        sr_wave = self.default_sampling_rate
        return wave, sr_wave
