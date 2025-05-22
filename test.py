import argparse
import wave
import numpy as np
from pathlib import Path
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores, LATEST_VERSION
from voicevox_engine.utility.path_utility import engine_root, get_save_dir
from voicevox_engine.model import AudioQuery


# === CẤU HÌNH TRỰC TIẾP ===
HOST = ""
PORT = 0  # Không sử dụng API
USE_GPU = False
VOICEVOX_DIR          = Path("/home/trungquang/open_avt_phuc/OpenAvatarChat/src/handlers/tts/voicevox/voicevox_engine/voicevox_core")           # nếu có
VOICELIB_DIRS         = None
RUNTIME_DIRS          = [Path("/home/trungquang/open_avt_phuc/OpenAvatarChat/src/handlers/tts/voicevox/voicevox_engine/onnxruntime/onnxruntime-linux-x64-1.13.1/lib"),]
ENABLE_MOCK = False
INIT_PROCESSES = 2
LOAD_ALL_MODELS = True
CPU_NUM_THREADS = 4
DISABLE_MUTABLE_API = False
# ==========================



def synthesize_to_file(text: str, speaker: int, sample_rate: int, output_wav: Path):
    # Khởi tạo core và engine
    core_mgr = initialize_cores(
        use_gpu=USE_GPU,
        voicelib_dirs=VOICELIB_DIRS,
        voicevox_dir=VOICEVOX_DIR,
        runtime_dirs=RUNTIME_DIRS,
        cpu_num_threads=CPU_NUM_THREADS,
        enable_mock=ENABLE_MOCK,
        load_all_models=True,
    )
    tts_manager = make_tts_engines_from_cores(core_mgr)

    # Lấy engine phiên bản mới nhất
    engine = tts_manager.get_tts_engine(LATEST_VERSION)

    # Tạo query cho synthesis
    accent_phrases = engine.create_accent_phrases(text, speaker)
    query = AudioQuery(
        accent_phrases=accent_phrases,
        speedScale=1.0,
        pitchScale=0.0,
        intonationScale=1.0,
        volumeScale=1.0,
        prePhonemeLength=0.1,
        postPhonemeLength=0.1,
        pauseLength=None,
        pauseLengthScale=1.0,
        outputSamplingRate=sample_rate,
        outputStereo=False,
        kana="",
    )

    # Tổng hợp
    wav_array = engine.synthesize(query)
    # wav_array: numpy array shape (channels, frames)

    # Ghi file WAV
    samples = (wav_array * 32767).astype(np.int16)
    with wave.open(str(output_wav), 'wb') as wf:
        wf.setnchannels(samples.shape[0])
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.T.tobytes())


def main():
    parser = argparse.ArgumentParser(description="Một script đơn giản để tổng hợp giọng nói bằng VOICEVOX mà không cần API.")
    parser.add_argument('--text', type=str, help='Văn bản cần tổng hợp', default="不動産は")
    parser.add_argument('--speaker', type=int, help='ID của speaker', default=1)
    parser.add_argument('--sample_rate', type=int, help='Tỷ lệ mẫu', default=24000)
    parser.add_argument('--output', type=Path, help='Đường dẫn file WAV đầu ra', default="/home/trungquang/open_avt_phuc/OpenAvatarChat/src/handlers/tts/voicevox/output.wav")
    args = parser.parse_args()

    synthesize_to_file(
        text=args.text,
        speaker=args.speaker,
        sample_rate=args.sample_rate,
        output_wav=args.output,
    )
    print(f"Đã sinh file: {args.output}")


if __name__ == '__main__':
    main()
