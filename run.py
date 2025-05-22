import multiprocessing
import warnings
from pathlib import Path

import uvicorn
from voicevox_engine.app.application import generate_app
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.engine_manifest import load_manifest
from voicevox_engine.library.library_manager import LibraryManager
from voicevox_engine.preset.preset_manager import PresetManager
from voicevox_engine.setting.setting_manager import USER_SETTING_PATH, SettingHandler
from voicevox_engine.tts_pipeline.song_engine import make_song_engines_from_cores
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
from voicevox_engine.user_dict.user_dict_manager import UserDictionary
from voicevox_engine.utility.path_utility import engine_manifest_path, engine_root, get_save_dir

# === CẤU HÌNH TRỰC TIẾP Ở ĐÂY ===
HOST                  = "0.0.0.0"
PORT                  = 50021
USE_GPU               = False
VOICEVOX_DIR          = Path("/home/trungquang/open_avt_phuc/OpenAvatarChat/src/handlers/tts/voicevox/voicevox_engine/voicevox_core")           # nếu có
VOICELIB_DIRS         = None
RUNTIME_DIRS          = [Path("/home/trungquang/open_avt_phuc/OpenAvatarChat/src/handlers/tts/voicevox/voicevox_engine/onnxruntime/onnxruntime-linux-x64-1.13.1/lib"),]
ENABLE_MOCK           = False
ENABLE_CANCELLABLE    = False
INIT_PROCESSES        = 2
LOAD_ALL_MODELS       = True
CPU_NUM_THREADS       = 4
OUTPUT_LOG_UTF8       = True
CORS_POLICY_MODE      = None
ALLOW_ORIGINS         = None
SETTING_FILE          = Path(USER_SETTING_PATH)
PRESET_FILE           = None
DISABLE_MUTABLE_API   = False
# ================================

def set_output_utf8():
    import sys
    from io import TextIOWrapper
    def _reconf(std):
        if isinstance(std, TextIOWrapper):
            std.reconfigure(encoding="utf-8", errors="backslashreplace")
        return std
    if sys.stdout: sys.stdout = _reconf(sys.stdout)
    if sys.stderr: sys.stderr = _reconf(sys.stderr)

def main():
    multiprocessing.freeze_support()
    if OUTPUT_LOG_UTF8:
        set_output_utf8()

    # Khởi tạo core và engine
    core_mgr    = initialize_cores(
        use_gpu=USE_GPU,
        voicelib_dirs=VOICELIB_DIRS,
        voicevox_dir=VOICEVOX_DIR,
        runtime_dirs=RUNTIME_DIRS,
        cpu_num_threads=CPU_NUM_THREADS,
        enable_mock=ENABLE_MOCK,
        load_all_models=LOAD_ALL_MODELS,
    )
    tts_engines = make_tts_engines_from_cores(core_mgr)
    song_engines= make_song_engines_from_cores(core_mgr)

    cancellable = None
    if ENABLE_CANCELLABLE:
        cancellable = CancellableEngine(
            init_processes=INIT_PROCESSES,
            use_gpu=USE_GPU,
            voicelib_dirs=VOICELIB_DIRS,
            voicevox_dir=VOICEVOX_DIR,
            runtime_dirs=RUNTIME_DIRS,
            cpu_num_threads=CPU_NUM_THREADS,
            enable_mock=ENABLE_MOCK,
        )

    settings = SettingHandler(SETTING_FILE).load()
    preset_path = PRESET_FILE or get_save_dir() / "presets.yaml"
    preset_mgr  = PresetManager(preset_path)
    user_dict   = UserDictionary()
    manifest    = load_manifest(engine_manifest_path())
    lib_mgr     = LibraryManager(
        get_save_dir() / "installed_libraries",
        manifest.supported_vvlib_manifest_version,
        manifest.brand_name,
        manifest.name,
        manifest.uuid,
    )
    root_dir    = VOICEVOX_DIR or engine_root()
    char_info   = (root_dir / "resources" / "character_info")
    if not char_info.exists():
        char_info = root_dir / "speaker_info"

    app = generate_app(
        tts_engines, song_engines, core_mgr,
        SettingHandler(SETTING_FILE), preset_mgr,
        user_dict, manifest, lib_mgr,
        cancellable,
        char_info,
        CORS_POLICY_MODE,
        ALLOW_ORIGINS,
        disable_mutable_api=DISABLE_MUTABLE_API,
    )

    uvicorn.run(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
