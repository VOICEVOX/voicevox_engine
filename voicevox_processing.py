# voicevox_processing.py

import threading
from pathlib import Path
from .voicevox_engine.core.core_initializer import initialize_cores
from .voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
import numpy as np

class VoiceVoxProcessor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls,
                voicelib_dirs: list[Path],
                runtime_dirs: list[Path],
                use_gpu: bool = False,
                cpu_num_threads: int | None = None,
                load_all_models: bool = False,
                sample_rate: int = 24000):
        # Singleton: chỉ init core 1 lần
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init(
                    voicelib_dirs, runtime_dirs, use_gpu, cpu_num_threads, load_all_models, sample_rate
                )
            return cls._instance

    def _init(self,
              voicelib_dirs: list[Path],
              runtime_dirs: list[Path],
              use_gpu: bool,
              cpu_num_threads: int | None,
              load_all_models: bool,
              sample_rate: int):
        # Khởi tạo core manager
        self.core_manager = initialize_cores(
            use_gpu=use_gpu,
            voicelib_dirs=voicelib_dirs,
            voicevox_dir=None,
            runtime_dirs=runtime_dirs,
            cpu_num_threads=cpu_num_threads,
            enable_mock=False,
            load_all_models=load_all_models
        )
        # Tạo TTS engine
        self.tts_engines = make_tts_engines_from_cores(self.core_manager)
        # Giữ sample_rate để padding nếu cần
        # self.sample_rate = self.tts_engines.get_sample_rate()  # giả sử API có method này
        self.sample_rate = sample_rate

    def synthesize(self, text: str, speaker_id: int) -> np.ndarray:
        """
        Trả về numpy array float32 shape (1, n_samples) với giá trị đã normalize [-1,1].
        """
        wav = self.tts_engines.synthesis(text=text, speaker=speaker_id)
        # ensure shape (1, T)
        if wav.ndim == 1:
            wav = wav[np.newaxis, :]
        return wav
