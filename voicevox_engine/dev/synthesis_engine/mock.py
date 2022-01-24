from logging import getLogger
from typing import Any, Dict, List

import numpy as np
from pyopenjtalk import tts
from scipy.signal import resample

from ...model import AccentPhrase, AudioQuery
from ...synthesis_engine import SynthesisEngineBase
from ...synthesis_engine.synthesis_engine import to_flatten_moras


class MockSynthesisEngine(SynthesisEngineBase):
    """
    SynthesisEngine [Mock]
    """

    def __init__(self, **kwargs):
        """
        __init__ [Mock]
        """
        super().__init__()

        self.speakers = kwargs["speakers"]
        self.supported_devices = kwargs["supported_devices"]
        self.default_sampling_rate = 24000

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        replace_phoneme_length 入力accent_phrasesを変更せずにそのまま返します [Mock]

        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            フレーズ句のリスト
        speaker_id : int
            話者

        Returns
        -------
        List[AccentPhrase]
            フレーズ句のリスト（変更なし）
        """
        return accent_phrases

    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        replace_mora_pitch 入力accent_phrasesを変更せずにそのまま返します [Mock]

        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            フレーズ句のリスト
        speaker_id : int
            話者

        Returns
        -------
        List[AccentPhrase]
            フレーズ句のリスト（変更なし）
        """
        return accent_phrases

    def synthesis(self, query: AudioQuery, speaker_id: int) -> np.ndarray:
        """
        synthesis voicevox coreを使わずに、音声合成する [Mock]

        Parameters
        ----------
        query : AudioQuery
            /audio_query APIで得たjson
        speaker_id : int
            話者

        Returns
        -------
        wave [npt.NDArray[np.int16]]
            音声波形データをNumPy配列で返します
        """
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
        参照→SynthesisEngine のdocstring [Mock]

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
        wave = resample(wave, 24000 * len(wave) // 48000)
        return wave
