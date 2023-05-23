## 目次

* [インストール](#インストール)
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


## インストール

このプロジェクトでは
* 3.11以上のpython
* poetry
* 依存ライブラリ
  * cmake
  * libsndfile1
* (実際に動かす時のみ)voicevox製品版
を使います。

#### セットアップ
以下のコマンドで使用できるようになります。

```console
git clone https://github.com/VOICEVOX/voicevox_engine.git
poetry install
```

## スクリプトの使い方

### 実行
コマンドライン引数の詳細は以下のコマンドで確認してください。

```console
python run.py --help
```

製品版 VOICEVOX でサーバーを起動
```console
VOICEVOX_DIR="C:/path/to/voicevox" # 製品版 VOICEVOX ディレクトリのパス
poetry run python run.py --voicevox_dir=$VOICEVOX_DIR
```

モックでサーバー起動
```console
poetry run python run.py --enable_mock
```

ログをUTF8に変更
```console
poetry run python run.py --output_log_utf8
```
もしくは
```console
VV_OUTPUT_LOG_UTF8=1
poetry run python run.py
```

### テスト
```console
poetry run pytest
```

### ビルド

この方法でビルドしたものは、リリースで公開されているものとは異なります。 また、GPUで利用するにはcuDNNやCUDA、DirectMLなどのライブラリが追加で必要となります。

```console
poetry install --with dev
OUTPUT_LICENSE_JSON_PATH=licenses.json \
bash build_util/create_venv_and_generate_licenses.bash
# ビルド自体はLIBCORE_PATH及びLIBONNXRUNTIME_PATHの指定がなくても可能です
LIBCORE_PATH="/path/to/libcore" \
    LIBONNXRUNTIME_PATH="/path/to/libonnxruntime" \
    pyinstaller --noconfirm run.spec
```


### コードフォーマット

このソフトウェアでは、リモートにプッシュする前にコードフォーマットを確認する仕組み(静的解析ツール)を利用できます。 利用するには、開発に必要なライブラリのインストールに加えて、以下のコマンドを実行してください。 プルリクエストを作成する際は、利用することを推奨します。

```console
poetry run pre-commit install -t pre-push
```

エラーが出た際は、以下のコマンドで修正することが可能です。なお、完全に修正できるわけではないので注意してください。

```console
poetry run pysen run format lint
```

### タイポチェック

typos を使ってタイポのチェックを行っています。 typos をインストール した後

```console
typos
```

でタイポチェックを行えます。 もし誤判定やチェックから除外すべきファイルがあれば 設定ファイルの説明 に従って_typos.tomlを編集してください。

### APIドキュメントの確認

API ドキュメント（実体はdocs/api/index.html）は自動で更新されます。
次のコマンドで API ドキュメントを手動で作成することができます。

```console
python make_docs.py
```


### 依存関係

Poetry を用いて依存ライブラリのバージョンを固定しています。 以下のコマンドで操作できます:

パッケージを追加する場合
```console
poetry add `パッケージ名`
poetry add --group dev `パッケージ名` # 開発依存の追加
poetry add --group test `パッケージ名` # テスト依存の追加
```

パッケージをアップデートする場合
```console
poetry update `パッケージ名`
poetry update # 全部更新
```

requirements.txtの更新
```console
poetry export --without-hashes -o requirements.txt # こちらを更新する場合は下３つも更新する必要があります。
poetry export --without-hashes --with dev -o requirements-dev.txt
poetry export --without-hashes --with test -o requirements-test.txt
poetry export --without-hashes --with license -o requirements-license.txt
```

### ユーザー辞書の更新について

以下のコマンドで openjtalk のユーザー辞書をコンパイルできます。

poetry run python -c "import pyopenjtalk; pyopenjtalk.create_user_dict('default.csv','user.dic')"


## Issue
不具合の報告、機能要望、改善提案、質問は<a href="https://github.com/VOICEVOX/voicevox_engine/issues/new">Issue</a>の方に報告してください。
