import copy
from logging import getLogger
from typing import Any, Dict, List

import numpy as np
from pyopenjtalk import tts
from soxr import resample

from ...core_adapter import CoreAdapter
from ...core_wrapper import CoreWrapper
from ...model import AccentPhrase, AudioQuery
from ...tts_pipeline import TTSEngineBase
from ...tts_pipeline.tts_engine import to_flatten_moras


class MockTTSEngine(TTSEngineBase):
    """
    TTSEngine [Mock]
    """

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self.core = CoreAdapter(core)
        # NOTE: self.coreは将来的に消す予定

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        replace_phoneme_length 入力accent_phrasesを変更せずにそのまま返します [Mock]

        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            フレーズ句のリスト
        style_id : int
            スタイルID

        Returns
        -------
        List[AccentPhrase]
            フレーズ句のリスト（変更なし）
        """
        return accent_phrases

    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        replace_mora_pitch 入力accent_phrasesを変更せずにそのまま返します [Mock]

        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            フレーズ句のリスト
        style_id : int
            スタイルID

        Returns
        -------
        List[AccentPhrase]
            フレーズ句のリスト（変更なし）
        """
        return accent_phrases

    def synthesis(
        self,
        query: AudioQuery,
        style_id: int,
        enable_interrogative_upspeak: bool = True,
    ) -> np.ndarray:
        """音声合成用のクエリに含まれる読み仮名に基づいてOpenJTalkで音声波形を生成する (Mock)"""
        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)

        # recall text in katakana
        flatten_moras = to_flatten_moras(query.accent_phrases)
        kana_text = "".join([mora.text for mora in flatten_moras])

        wave = self.forward(kana_text)

        # volume
        wave *= query.volumeScale

        return wave.astype("int16")

    def forward(self, text: str, **kwargs: Dict[str, Any]) -> np.ndarray:
        """
        forward tts via pyopenjtalk.tts()
        参照→TTSEngine のdocstring [Mock]

        Parameters
        ----------
        text : str
            入力文字列（例：読み上げたい文章をカタカナにした文字列、等）

        Returns
        -------
        wave [npt.NDArray[np.int16]]
            音声波形データをNumPy配列で返します

        Note
        -------
        ここで行う音声合成では、調声（ピッチ等）を反映しない

        # pyopenjtalk.tts()の出力仕様
        dtype=np.float64, 16 bit, mono 48000 Hz

        # resampleの説明
        非モック実装（decode_forward）と合わせるために、出力を24kHzに変換した。
        """
        logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
        logger.info("[Mock] input text: %s" % text)
        wave, sr = tts(text)
        wave = resample(wave, 48000, 24000)
        return wave
