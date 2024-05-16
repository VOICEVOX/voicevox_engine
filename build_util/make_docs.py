import json
from pathlib import Path

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.SettingLoader import USER_SETTING_PATH, SettingHandler
from voicevox_engine.user_dict.user_dict import UserDictionary
from voicevox_engine.utility.path_utility import engine_root


def generate_api_docs_html(schema: str) -> str:
    """OpenAPI schema から API ドキュメント HTML を生成する"""

    return (
        """<!DOCTYPE html>
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
        Redoc.init(%s, {"hideHostname": true}, document.getElementById("redoc-container"));
    </script>
</body>
</html>"""
        % schema
    )


if __name__ == "__main__":
    cores = CoreManager()
    cores.register_core(CoreAdapter(MockCoreWrapper()), "mock")
    # FastAPI の機能を用いて OpenAPI schema を生成する
    app = generate_app(
        tts_engines={"mock": MockTTSEngine()},
        cores=cores,
        latest_core_version="mock",
        setting_loader=SettingHandler(USER_SETTING_PATH),
        preset_manager=PresetManager(  # FIXME: impl MockPresetManager
            preset_path=engine_root() / "presets.yaml",
        ),
        user_dict=UserDictionary(),
    )
    api_schema = json.dumps(app.openapi())

    # API ドキュメント HTML を生成する
    api_docs_html = generate_api_docs_html(api_schema)

    # HTML ファイルとして保存する
    api_docs_root = Path("docs/api")  # 'upload-docs' workflow の対象
    output_path = api_docs_root / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(api_docs_html)
