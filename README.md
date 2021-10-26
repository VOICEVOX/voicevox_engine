# VOICEVOX ENGINE

[![build](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/build.yml/badge.svg)](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/build.yml)
[![releases](https://img.shields.io/github/v/release/Hiroshiba/voicevox_engine)](https://github.com/Hiroshiba/voicevox_engine/releases)

[![test](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/test.yml/badge.svg)](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/Hiroshiba/voicevox_engine/badge.svg)](https://coveralls.io/github/Hiroshiba/voicevox_engine)

[![build-docker](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/build-docker.yml/badge.svg)](https://github.com/Hiroshiba/voicevox_engine/actions/workflows/build-docker.yml)
[![docker](https://img.shields.io/docker/pulls/hiroshiba/voicevox_engine)](https://hub.docker.com/r/hiroshiba/voicevox_engine)


[VOICEVOX](https://github.com/Hiroshiba/voicevox)の音声合成エンジン。
実態は HTTP サーバーなので、リクエストを送信すればテキスト音声合成できます。

## API ドキュメント

VOICEVOX ソフトウェアを起動した状態で、ブラウザから http://localhost:50021/docs にアクセスするとドキュメントが表示されます。  
[VOICEVOX 音声合成エンジンとの連携](./docs/VOICEVOX音声合成エンジンとの連携.md)も参考になるかもしれません。

### HTTP リクエストで音声合成するサンプルコード

```bash
echo -n "こんにちは、音声合成の世界へようこそ" >text.txt

curl -s \
    -X POST \
    "localhost:50021/audio_query?speaker=1"\
    --get --data-urlencode text@text.txt \
    > query.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    localhost:50021/synthesis?speaker=1 \
    > audio.wav
```

### 読み方を AquesTalk 記法で取得・修正するサンプルコード

`/audio_query`のレスポンスにはエンジンが判断した読み方が AquesTalk ライクな記法([本家の記法](https://www.a-quest.com/archive/manual/siyo_onseikigou.pdf)とは一部異なります)で記録されています。
記法は次のルールに従います。

- 全てのカナはカタカナで記述される
- アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
- カナの手前に`_`を入れるとそのカナは無声化される
- アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を 1 つ指定する必要がある。

```bash
# 読ませたい文章をutf-8でtext.txtに書き出す
echo -n "ディープラーニングは万能薬ではありません" >text.txt

curl -s \
    -X POST \
    "localhost:50021/audio_query?speaker=1" \
    --get --data-urlencode text@text.txt \
    > query.json

cat query.json | grep -o -E "\"kana\":\".*\""
# 結果... "kana":"ディ'イプ/ラ'アニングワ/バンノオヤクデワアリマセ'ン"

# "ディイプラ'アニングワ/バンノ'オヤクデワ/アリマセ'ン"と読ませたいので、
# is_kana=trueをつけてイントネーションを取得しnewphrases.jsonに保存
echo -n "ディイプラ'アニングワ/バンノ'オヤクデワ/アリマセ'ン" > kana.txt
curl -s \
    -X POST \
    "localhost:50021/accent_phrases?speaker=1&is_kana=true" \
    --get --data-urlencode text@kana.txt \
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

### 2人の話者でモーフィングするサンプルコード

`/synthesis_morphing`では、2人の話者でそれぞれ合成された音声を元に、モーフィングした音声を生成します。

```bash
echo -n "モーフィングを利用することで、２つの声を混ぜることができます。" > text.txt

curl -s \
    -X POST \
    "localhost:50021/audio_query?speaker=0"\
    --get --data-urlencode text@text.txt \
    > query.json

# 元の話者での合成結果
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "localhost:50021/synthesis?speaker=0" \
    > audio.wav

export MORPH_RATE=0.5

# 話者2人分の音声合成+WORLDによる音声分析が入るため時間が掛かるので注意
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "localhost:50021/synthesis_morphing?base_speaker=0&target_speaker=1&morph_rate=$MORPH_RATE" \
    > audio.wav

export MORPH_RATE=0.9

# query、base_speaker、target_speakerが同じ場合はキャッシュが使用されるため比較的高速に生成される
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "localhost:50021/synthesis_morphing?base_speaker=0&target_speaker=1&morph_rate=$MORPH_RATE" \
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

python generate_licenses.py > licenses.json

python -m nuitka \
    --standalone \
    --plugin-enable=numpy \
    --follow-import-to=numpy \
    --follow-import-to=aiofiles \
    --include-package=uvicorn \
    --include-package=anyio \
    --include-package-data=pyopenjtalk \
    --include-package-data=resampy \
    --include-data-file=VERSION.txt=./ \
    --include-data-file=licenses.json=./ \
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
## 依存関係の更新について

pip-toolsが必要です。

```bash
pip install pip-tools
```

以下のコマンドで更新できます。

```bash
pip-compile requirements.in
pip-compile requirements-dev.in
pip-compile requirements-test.in
```


## プリセット機能について

run.exeと同じ場所に`presets.yaml`を配置します。  
例となるファイル(`presets-template.yaml`)がありますので参照してください。
(エンジン起動後にファイルを書き換えるとエンジンにも反映されます)   
注意点として、`id`は重複してはいけません。  
`speaker_uuid`は、`/speakers`で確認できます。  
また、エンジンが保持しているプリセットの設定は、`/presets`で取得できます。

このプリセットは、AudioQueryを取得する際に使用します。  
`/audio_query_from_preset?preset_id=1`のようになります。   
後は、通常と同じように`/synthesis`にAudioQueryとspeaker引数を投げて下さい。

## GitHub Actions

### Secrets

| name               | description                                                             |
| :----------------- | :---------------------------------------------------------------------- |
| DOCKERHUB_USERNAME | Docker Hub ユーザ名                                                     |
| DOCKERHUB_TOKEN    | [Docker Hub アクセストークン](https://hub.docker.com/settings/security) |

## ライセンス

LGPL v3 と、ソースコードの公開が不要な別ライセンスのデュアルライセンスです。
別ライセンスを取得したい場合は、ヒホ（twitter: @hiho_karuta）に求めてください。
