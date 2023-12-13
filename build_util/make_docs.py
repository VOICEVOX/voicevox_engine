import json
from pathlib import Path

from voicevox_engine.dev.core import mock as core
from voicevox_engine.dev.synthesis_engine.mock import MockTTSEngine
from voicevox_engine.preset import PresetManager
from voicevox_engine.setting import USER_SETTING_PATH, SettingLoader
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

    # FastAPI機能を用いた OpenAPI schema の生成
    app = run.generate_app(
        synthesis_engines={"mock": MockTTSEngine(speakers=core.metas())},
        latest_core_version="mock",
        setting_loader=SettingLoader(USER_SETTING_PATH),
        preset_manager=PresetManager(  # FIXME: impl MockPresetManager
            preset_path=engine_root() / "presets.yaml",
        ),
    )
    api_schema = json.dumps(app.openapi())

    # APIドキュメントHTMLを生成する
    api_docs_html = generate_api_docs_html(api_schema)

    # HTMLファイルとして保存する
    api_docs_root = Path("docs/api")  # 'upload-docs' workflow の対象
    output_path = api_docs_root / "index.html"
    with open(output_path, "w") as f:
        f.write(api_docs_html)
