**このガイドラインは現在工事中です。**

TODO: 重複部分を省く

## 目次

* [環境構築](#環境構築)
* [スクリプトの使い方](#スクリプトの使い方)
  * [実行](#実行)
  * [テスト](#テスト)
  * [ビルド](#ビルド)
  * [コードフォーマット](#コードフォーマット)
  * [タイポチェック](#タイポチェック)
  * [APIドキュメントの確認](#APIドキュメントの確認)
  * [依存関係](#依存関係)
  * [ユーザー辞書の更新について](#ユーザー辞書の更新について)
* [Issue](#issue)

## 貢献者の方へ

Issue を解決するプルリクエストを作成される際は、別の方と同じ Issue に取り組むことを避けるため、
Issue 側で取り組み始めたことを伝えるか、最初に Draft プルリクエストを作成してください。

[VOICEVOX 非公式 Discord サーバー](https://discord.gg/WMwWetrzuh)にて、開発の議論や雑談を行っています。気軽にご参加ください。

## 環境構築
`Python 3.11.3` を用いて開発されています。
インストールするには、各 OS ごとの C/C++ コンパイラ、CMake が必要になります。

```bash
# レポジトリのクローン
git clone https://github.com/VOICEVOX/voicevox_engine.git
cd ./voicevox_engine

# 実行・開発・テスト環境のインストール
python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-test.txt
```

<!-- このプロジェクトでは
* `Python 3.11.3`
* 依存ライブラリ
  * cmake
  * libsndfile1
* (実際に動かす時のみ)製品版 VOICEVOX
を使います。 -->

OSS 版 VOICEVOX ENGINE は製品版 VOICEVOX の音声モデルを含んでいません。  
これら音声モデルは、利用規約を遵守の上、以下の手順で製品版 VOICEVOX CORE を導入することにより利用できます。  
なお、VOICEVOX ENGINE 単体でもモック利用により起動自体は可能です。  

1. 環境変数をセットする

* `VERSION`: voicevox_core のバージョン (例: `0.15.0`)
* `OS`: OS 種別 (`windows` | `osx` | `linux`)
* `ARCHITECTURE`: CPU アーキテクチャ (`x86` | `x64` | `arm64`)
* `PROCESSOR`: プロセッサ種別 (`cpu` | `gpu` | `cuda` | `directml`)

例（x64 Linux マシン向け VOICEVOX CORE v0.15.0 CPU版）:  
```bash
VERSION="0.15.0"; OS="linux"; ARCHITECTURE="x64"; PROCESSOR="cpu";
```

2. 製品版 VOICEVOX CORE をダウンロード・展開する

```bash
CORENAME="voicevox_core-${OS}-${ARCHITECTURE}-${PROCESSOR}-${VERSION}"
curl -L "https://github.com/VOICEVOX/voicevox_core/releases/download/${VERSION}/${CORENAME}.zip" -o "${CORENAME}.zip"
unzip "${CORENAME}.zip"
VOICELIB_DIR_1=$CORENAME
```

最新のリリースは以下にあります。
https://github.com/VOICEVOX/voicevox_core/releases/latest

    
## スクリプトの使い方

### 実行
コマンドライン引数の詳細は以下のコマンドで確認してください。

```bash
python run.py --help
```

製品版 VOICEVOX でサーバーを起動
```bash
VOICEVOX_DIR="C:/path/to/voicevox" # 製品版 VOICEVOX ディレクトリのパス
python run.py --voicevox_dir=$VOICEVOX_DIR
```

製品版 VOICEVOX CORE を読み込んでサーバーを起動
```bash
VOICELIB_DIR_1="C:/path/to/core_1"; VOICELIB_DIR_2="C:/path/to/core_2"; # 製品版 VOICEVOX CORE ディレクトリのパス
python run.py --voicelib_dir=$VOICELIB_DIR_1 --voicelib_dir=$VOICELIB_DIR_2
```

<!-- 差し替え可能な音声ライブラリまたはその仕様が公開されたらコメントを外す
```bash
# 音声ライブラリを差し替える
VOICELIB_DIR="C:/path/to/your/tts-model"
python run.py --voicevox_dir=$VOICEVOX_DIR --voicelib_dir=$VOICELIB_DIR
```
-->

モックでサーバー起動
```bash
python run.py --enable_mock
```

ログをUTF8に変更
```bash
python run.py --output_log_utf8
# もしくは
VV_OUTPUT_LOG_UTF8=1 python run.py
```

### テスト
```bash
python -m pytest
```

#### スナップショットの更新

```bash
python -m pytest --snapshot-update
```

### ビルド

この方法でビルドしたものは、リリースで公開されているものとは異なります。 また、GPUで利用するにはcuDNNやCUDA、DirectMLなどのライブラリが追加で必要となります。

```bash
OUTPUT_LICENSE_JSON_PATH=licenses.json \
bash build_util/create_venv_and_generate_licenses.bash

# モックでビルドする場合
pyinstaller --noconfirm run.spec

# 製品版でビルドする場合
CORE_MODEL_DIR_PATH="/path/to/core_model" \
LIBCORE_PATH="/path/to/libcore" \
LIBONNXRUNTIME_PATH="/path/to/libonnxruntime" \
pyinstaller --noconfirm run.spec  
```

#### Github Actions でビルド

fork したリポジトリで Actions を ON にし、workflow_dispatch で`build.yml`を起動すればビルドできます。
成果物は Release にアップロードされます。

### コードフォーマット

このソフトウェアでは、リモートにプッシュする前にコードフォーマットを確認する仕組み(静的解析ツール)を利用できます。 利用するには、開発に必要なライブラリのインストールに加えて、以下のコマンドを実行してください。 プルリクエストを作成する際は、利用することを推奨します。

```bash
pre-commit install -t pre-push
```

エラーが出た際は、以下のコマンドで修正することが可能です。なお、完全に修正できるわけではないので注意してください。

```bash
pysen run format lint
```

### タイポチェック

[typos](https://github.com/crate-ci/typos) を使ってタイポのチェックを行っています。 [typos をインストール](https://github.com/crate-ci/typos#install) した後

```bash
typos
```

でタイポチェックを行えます。 もし誤判定やチェックから除外すべきファイルがあれば [設定ファイルの説明](https://github.com/crate-ci/typos#false-positives) に従って`_typos.toml`を編集してください。

### APIドキュメントの確認

API ドキュメント（実体はdocs/api/index.html）は自動で更新されます。
次のコマンドで API ドキュメントを手動で作成することができます。

```bash
PYTHONPATH=. python build_util/make_docs.py
```


### 依存関係

[Poetry](https://python-poetry.org/) を用いて依存ライブラリのバージョンを固定しています。 以下のコマンドで操作できます:

パッケージを追加する場合
```bash
poetry add `パッケージ名`
poetry add --group dev `パッケージ名` # 開発依存の追加
poetry add --group test `パッケージ名` # テスト依存の追加
```

パッケージをアップデートする場合
```bash
poetry update `パッケージ名`
poetry update # 全部更新
```

requirements.txtの更新
```bash
poetry export --without-hashes -o requirements.txt # こちらを更新する場合は下３つも更新する必要があります。
poetry export --without-hashes --with dev -o requirements-dev.txt
poetry export --without-hashes --with test -o requirements-test.txt
poetry export --without-hashes --with license -o requirements-license.txt
```

#### ライセンス

依存ライブラリは「コアビルド時にリンクして一体化しても、コア部のコード非公開 OK」なライセンスを持つ必要があります。  
主要ライセンスの可否は以下の通りです。

- MIT/Apache/BSD-3: OK
- LGPL: OK （コアと動的分離されているため）
- GPL: NG （全関連コードの公開が必要なため）

### API ドキュメントの確認

[API ドキュメント](https://voicevox.github.io/voicevox_engine/api/)（実体は`docs/api/index.html`）は自動で更新されます。  
次のコマンドで API ドキュメントを手動で作成することができます。

```bash
PYTHONPATH=. python build_util/make_docs.py
```

### GitHub Actions

#### Variables

| name               | description         |
| :----------------- | :------------------ |
| DOCKERHUB_USERNAME | Docker Hub ユーザ名 |

#### Secrets

| name            | description                                                             |
| :-------------- | :---------------------------------------------------------------------- |
| DOCKERHUB_TOKEN | [Docker Hub アクセストークン](https://hub.docker.com/settings/security) |

## Issue
不具合の報告、機能要望、改善提案、質問は<a href="https://github.com/VOICEVOX/voicevox_engine/issues/new">Issue</a>の方に報告してください。

## ライセンス

LGPL v3 と、ソースコードの公開が不要な別ライセンスのデュアルライセンスです。
別ライセンスを取得したい場合は、ヒホに求めてください。  
X アカウント: [@hiho_karuta](https://x.com/hiho_karuta)
