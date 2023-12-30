import json
from pathlib import Path

from voicevox_engine.dev.core import MockCoreWrapper
from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.preset import PresetManager
from voicevox_engine.setting import USER_SETTING_PATH, SettingLoader
from voicevox_engine.tts_pipeline.tts_engine import CoreAdapter
from voicevox_engine.utility import engine_root


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

    import run

    mock_core = MockCoreWrapper()
    # FastAPI の機能を用いて OpenAPI schema を生成する
    app = run.generate_app(
        tts_engines={"mock": MockTTSEngine(mock_core)},
        cores={"mock": CoreAdapter(mock_core)},
        latest_core_version="mock",
        setting_loader=SettingLoader(USER_SETTING_PATH),
        preset_manager=PresetManager(  # FIXME: impl MockPresetManager
            preset_path=engine_root() / "presets.yaml",
        ),
    )
    api_schema = json.dumps(app.openapi())

    # API ドキュメント HTML を生成する
    api_docs_html = generate_api_docs_html(api_schema)

    # HTML ファイルとして保存する
    api_docs_root = Path("docs/api")  # 'upload-docs' workflow の対象
    output_path = api_docs_root / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(api_docs_html)
