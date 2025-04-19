"""ドキュメントファイルを生成する。"""
# TODO: 目的を「ドキュメント生成」から「API ドキュメント生成」へ変更し、ファイル名等をそれに合わせられるか検討

import json
from pathlib import Path

from fastapi import FastAPI

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.engine_manifest import load_manifest
from voicevox_engine.library.library_manager import LibraryManager
from voicevox_engine.preset.preset_manager import PresetManager
from voicevox_engine.setting.setting_manager import USER_SETTING_PATH, SettingHandler
from voicevox_engine.tts_pipeline.song_engine import SongEngineManager
from voicevox_engine.tts_pipeline.tts_engine import TTSEngineManager
from voicevox_engine.user_dict.user_dict_manager import UserDictionary
from voicevox_engine.utility.path_utility import engine_manifest_path, get_save_dir


def _generate_mock_app() -> FastAPI:
    """app インスタンスをモック設定で生成する。"""
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "mock")
    tts_engines = TTSEngineManager()
    song_engines = SongEngineManager()
    tts_engines.register_engine(MockTTSEngine(), "mock")
    preset_path = get_save_dir() / "presets.yaml"
    engine_manifest = load_manifest(engine_manifest_path())
    library_manager = LibraryManager(
        get_save_dir() / "installed_libraries",
        engine_manifest.supported_vvlib_manifest_version,
        engine_manifest.brand_name,
        engine_manifest.name,
        engine_manifest.uuid,
    )
    app = generate_app(
        tts_engines=tts_engines,
        song_engines=song_engines,
        core_manager=core_manager,
        setting_loader=SettingHandler(USER_SETTING_PATH),
        preset_manager=PresetManager(preset_path),
        user_dict=UserDictionary(),
        engine_manifest=engine_manifest,
        library_manager=library_manager,
    )
    return app


def _get_openapi_schema(app: FastAPI) -> str:
    """OpenAPI スキーマを取得する。"""
    # FastAPI の機能を用いる
    return json.dumps(app.openapi())


def _generate_api_docs_html(schema: str) -> str:
    """OpenAPI schema から API ドキュメント HTML を生成する"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <title>voicevox_engine API Document</title>
    <meta charset="utf-8">
    <link rel="shortcut icon" href="https://voicevox.hiroshiba.jp/favicon-32x32.png">
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"></script>
    <script>
        Redoc.init({schema}, {{"hideHostname": true}}, document.getElementById("redoc-container"));
    </script>
</body>
</html>"""


def _save_as_html_file(api_docs_str: str) -> None:
    """HTML 文字列を HTML ファイルとして保存する。"""
    api_docs_root = Path("docs/api")  # 'upload-docs' workflow の対象
    output_path = api_docs_root / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(api_docs_str)


def _generate_api_docs() -> None:
    app = _generate_mock_app()
    api_schema = _get_openapi_schema(app)
    api_docs_html = _generate_api_docs_html(api_schema)
    _save_as_html_file(api_docs_html)


def main() -> None:
    """ドキュメントファイルを生成する。"""
    _generate_api_docs()


if __name__ == "__main__":
    main()
