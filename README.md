# VOICEVOX ENGINE

[VOICEVOX](https://github.com/Hiroshiba/voicevox)の音声合成エンジン。
実態は HTTP サーバーなので、リクエストを送信すればテキスト音声合成できます。

## API ドキュメント

VOICEVOX ソフトウェアを起動した状態で、ブラウザから http://localhost:50021/docs にアクセスするとドキュメントが表示されます。  
[VOICEVOX 音声合成エンジンとの連携](./docs/VOICEVOX音声合成エンジンとの連携.md)も参考になるかもしれません。

### HTTP リクエストで音声合成するサンプルコード

```bash
text="ABCDEFG"

curl -s \
    -X POST \
    "localhost:50021/audio_query?text=$text&speaker=1"\
    > query.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    localhost:50021/synthesis?speaker=1 \
    > audio.wav
```

## 貢献者の方へ

Issue を解決するプルリクエストを作成される際は、別の方と同じ Issue に取り組むことを避けるため、
Issue 側で取り組み始めたことを伝えるか、最初に Draft プルリクエストを作成してください。

## 環境構築

```bash
# 開発に必要なライブラリのインストール
pip install -r requirements-test.txt

# とりあえず実行したいだけなら代わりにこちら
pip install -r requirements.txt
```

## 実行

```bash
# 製品版 VOICEVOX でサーバーを起動
VOICEVOX_DIR="C:/path/to/voicevox" # 製品版 VOICEVOX ディレクトリのパス
python run.py --voicevox_dir=$VOICEVOX_DIR
```

<!-- 差し替え可能な音声ライブラリまたはその仕様が公開されたらコメントを外す
```bash
# 音声ライブラリを差し替える
VOICELIB_DIR="C:/path/to/your/tts-model"
python run.py --voicevox_dir=$VOICEVOX_DIR --voicelib_dir=$VOICELIB_DIR
```
-->

```bash
# モックでサーバー起動
python run.py
```

## コードフォーマット

コードのフォーマットを整えます。プルリクエストを送る前に実行してください。

```bash
pysen run format lint
```

## ビルド

Build Tools for Visual Studio 2019 が必要です。

```bash
pip install -r requirements-dev.txt

python -m nuitka \
    --standalone \
    --plugin-enable=numpy \
    --follow-import-to=numpy \
    --follow-import-to=aiofiles \
    --include-package=uvicorn \
    --include-package-data=pyopenjtalk \
    --include-data-file=VERSION.txt=./ \
    --include-data-file=C:/音声ライブラリへのパス/Release/*.dll=./ \
    --include-data-file=C:/音声ライブラリへのパス/*.bin=./ \
    --include-data-dir=.venv/Lib/site-packages/_soundfile_data=./_soundfile_data \
    --msvc=14.2 \
    --follow-imports \
    --no-prefer-source-code \
    run.py
```

## ライセンス

LGPL v3 と、ソースコードの公開が不要な別ライセンスのデュアルライセンスです。
別ライセンスを取得したい場合は、ヒホ（twitter: @hiho_karuta）に求めてください。
