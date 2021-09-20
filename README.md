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

### 読み方をAquesTalk記法で取得・修正するサンプルコード
`/audio_query`のレスポンスにはエンジンが判断した読み方がAquesTalkライクな記法([本家の記法](https://www.a-quest.com/archive/manual/siyo_onseikigou.pdf)とは一部異なります)で記録されています。
記法は次のルールに従います。

* 全てのカナはカタカナで記述される
* アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
* カナの手前に`_`を入れるとそのカナは無声化される
* アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。


```bash
# "ディープラーニングは万能薬ではありません"をURLエンコード
text="%E3%83%87%E3%82%A3%E3%83%BC%E3%83%97%E3%83%A9%E3%83%BC%E3%83%8B%E3%83%B3%E3%82%B0%E3%81%AF%E4%B8%87%E8%83%BD%E8%96%AC%E3%81%A7%E3%81%AF%E3%81%82%E3%82%8A%E3%81%BE%E3%81%9B%E3%82%93"

curl -s \
    -X POST \
    "localhost:50021/audio_query?text=$text&speaker=1"\
    > query.json
    
cat query.json | grep -o -E "\"kana\":\".*\""
# 結果... "kana":"ディ'イプ/ラ'アニングワ/バンノオヤクデワアリマセ'ン"

# "ディイプラ'アニングワ/バンノ'オヤクデワ/アリマセ'ン"に修正しURLエンコード
kana="%E3%83%87%E3%82%A3%E3%82%A4%E3%83%97%E3%83%A9'%E3%82%A2%E3%83%8B%E3%83%B3%E3%82%B0%E3%83%AF%2F%E3%83%90%E3%83%B3%E3%83%8E'%E3%82%AA%E3%83%A4%E3%82%AF%E3%83%87%E3%83%AF%2F%E3%82%A2%E3%83%AA%E3%83%9E%E3%82%BB'%E3%83%B3"

curl -s \
    -X POST \
    "localhost:50021/accent_phrases?text=$kana&speaker=1&is_kana=true"\
    > newphrases.json
    
# query.jsonの"accent_phrases"の内容をnewphrases.jsonの内容に置き換える
cat query.json | sed -e "s/\[{.*}\]/$(cat newphrases.json)/g" > newquery.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @newquery.json \
    localhost:50021/synthesis?speaker=1 \
    > audio.wav
```

## Docker イメージ

### CPU

```bash
docker pull hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest
docker run --rm -it -p '127.0.0.1:50021:50021' hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest
```

### GPU

```bash
docker pull hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest
docker run --rm --gpus all -p '127.0.0.1:50021:50021' hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest
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
    --include-package-data=resampy \
    --include-data-file=VERSION.txt=./ \
    --include-data-file=C:/path/to/cuda/*.dll=./ \
    --include-data-file=C:/path/to/libtorch/*.dll=./ \
    --include-data-file=C:/音声ライブラリへのパス/*.bin=./ \
    --include-data-file=C:/音声ライブラリへのパス/metas.json=./ \
    --include-data-dir=.venv/Lib/site-packages/_soundfile_data=./_soundfile_data \
    --include-data-file=.venv-release/Lib/site-packages/llvmlite/binding/llvmlite.dll=./ \
    --msvc=14.2 \
    --follow-imports \
    --no-prefer-source-code \
    run.py
```

## GitHub Actions

### Secrets

| name               | description                                                             |
| :----------------- | :---------------------------------------------------------------------- |
| DOCKERHUB_USERNAME | Docker Hub ユーザ名                                                     |
| DOCKERHUB_TOKEN    | [Docker Hub アクセストークン](https://hub.docker.com/settings/security) |

## ライセンス

LGPL v3 と、ソースコードの公開が不要な別ライセンスのデュアルライセンスです。
別ライセンスを取得したい場合は、ヒホ（twitter: @hiho_karuta）に求めてください。
