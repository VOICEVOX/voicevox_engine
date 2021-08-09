# VOICEVOX ENGINE

[VOICEVOX](https://github.com/Hiroshiba/voicevox)の音声合成エンジン。
ただのHTTPサーバーなので、リクエストを送信すればテキスト音声合成できます。

## APIドキュメント

VOICEVOXソフトウェアを起動した状態で、ブラウザから http://localhost:50021/docs にアクセスするとドキュメントが表示されます。

## 環境構築

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## 実行

TODO: `each_cpp_forwarder`のインターフェースを載せる

```bash
python run.py  # 2021/08/08 17:50現在、実行はできますが音声合成はできません。
```

## ビルド

Build Tools for Visual Studio 2019 が必要です。

```bash
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
