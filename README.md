# VOICEVOX ENGINE

[![build](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine.yml)
[![releases](https://img.shields.io/github/v/release/VOICEVOX/voicevox_engine)](https://github.com/VOICEVOX/voicevox_engine/releases)
[![discord](https://img.shields.io/discord/879570910208733277?color=5865f2&label=&logo=discord&logoColor=ffffff)](https://discord.gg/WMwWetrzuh)

[![test](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/VOICEVOX/voicevox_engine/badge.svg)](https://coveralls.io/github/VOICEVOX/voicevox_engine)

[![build-docker](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-container.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-container.yml)
[![docker](https://img.shields.io/docker/pulls/voicevox/voicevox_engine)](https://hub.docker.com/r/voicevox/voicevox_engine)

[VOICEVOX](https://voicevox.hiroshiba.jp/) のエンジンです。  
実態は HTTP サーバーなので、リクエストを送信すればテキスト音声合成できます。

（エディターは [VOICEVOX](https://github.com/VOICEVOX/voicevox/) 、
コアは [VOICEVOX CORE](https://github.com/VOICEVOX/voicevox_core/) 、
全体構成は [こちら](https://github.com/VOICEVOX/voicevox/blob/main/docs/%E5%85%A8%E4%BD%93%E6%A7%8B%E6%88%90.md) に詳細があります。）

## 目次

目的に合わせたガイドはこちらです。

- [ユーザーガイド](./USER_GUIDE.md): 音声合成をしたい方向け
- [貢献者ガイド](#貢献者ガイド): コントリビュートしたい方向け
- [開発者ガイド](#開発者ガイド): コードを利用したい方向け
- [マルチエンジン機能ガイド](./MULTIENGINE_GUIDE.md): 自作などの音声合成エンジンを VOICEVOX エディターで動かしたい方向け

## ユーザーガイド

音声合成をしたい方向けの使い方は [USER_GUIDE.md](./USER_GUIDE.md) をご覧ください。

## 貢献者ガイド

VOICEVOX ENGINE は皆さんのコントリビューションをお待ちしています！  
詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) をご覧ください。  
また [VOICEVOX 非公式 Discord サーバー](https://discord.gg/WMwWetrzuh)にて、開発の議論や雑談を行っています。気軽にご参加ください。

なお、Issue を解決するプルリクエストを作成される際は、別の方と同じ Issue に取り組むことを避けるため、Issue 側で取り組み始めたことを伝えるか、最初に Draft プルリクエストを作成することを推奨しています。

## 開発者ガイド

### 環境構築

`Python 3.11.9` を用いて開発されています。
インストールするには、各 OS ごとの C/C++ コンパイラ、CMake が必要になります。

パッケージ管理ツールに [uv](https://docs.astral.sh/uv/) を使用しています。
uv のインストール方法については[公式ドキュメント](https://docs.astral.sh/uv/getting-started/installation/)を参考にしてください。

```bash
# 実行環境のインストール
uv sync

# 開発環境・テスト環境・ビルド環境のインストール
uv sync --all-groups
```

### 実行

コマンドライン引数の詳細は以下のコマンドで確認してください。

```bash
uv run run.py --help
```

```bash
# 製品版 VOICEVOX でサーバーを起動
VOICEVOX_DIR="C:/path/to/VOICEVOX/vv-engine" # 製品版 VOICEVOX ディレクトリ内の ENGINE のパス
uv run run.py --voicevox_dir=$VOICEVOX_DIR
```

<!-- 差し替え可能な音声ライブラリまたはその仕様が公開されたらコメントを外す
```bash
# 音声ライブラリを差し替える
VOICELIB_DIR="C:/path/to/your/tts-model"
uv run run.py --voicevox_dir=$VOICEVOX_DIR --voicelib_dir=$VOICELIB_DIR
```
-->

```bash
# モックでサーバー起動
uv run run.py --enable_mock
```

```bash
# ログをUTF8に変更
uv run run.py --output_log_utf8
# もしくは VV_OUTPUT_LOG_UTF8=1 uv run run.py
```

#### CPU スレッド数を指定する

CPU スレッド数が未指定の場合は、論理コア数の半分が使われます。  
Windows と Linux では性能の高い CPU を優先して使おうとします。  
もし IaaS 上で実行していたり、専用サーバーで実行している場合など、  
エンジンが使う処理能力を調節したい場合は、CPU スレッド数を指定することで実現できます。

- コマンドライン引数で指定する
  ```bash
  uv run run.py --voicevox_dir=$VOICEVOX_DIR --cpu_num_threads=4
  ```
- 環境変数で指定する
  ```bash
  export VV_CPU_NUM_THREADS=4
  uv run run.py --voicevox_dir=$VOICEVOX_DIR
  ```

#### 過去のバージョンのコアを使う

VOICEVOX Core 0.5.4 以降のコアを使用する事が可能です。  
Mac での libtorch 版コアのサポートはしていません。

##### 過去のバイナリを指定する

製品版 VOICEVOX もしくはコンパイル済みエンジンのディレクトリを`--voicevox_dir`引数で指定すると、そのバージョンのコアが使用されます。

```bash
uv run run.py --voicevox_dir="/path/to/VOICEVOX/vv-engine"
```

Mac では、`DYLD_LIBRARY_PATH`の指定が必要です。

```bash
DYLD_LIBRARY_PATH="/path/to/voicevox" uv run run.py --voicevox_dir="/path/to/VOICEVOX/vv-engine"
```

##### 音声ライブラリを直接指定する

[VOICEVOX Core の zip ファイル](https://github.com/VOICEVOX/voicevox_core/releases)を解凍したディレクトリを`--voicelib_dir`引数で指定します。  
また、コアのバージョンに合わせて、[libtorch](https://pytorch.org/)や[onnxruntime](https://github.com/microsoft/onnxruntime) (共有ライブラリ) のディレクトリを`--runtime_dir`引数で指定します。  
ただし、システムの探索パス上に libtorch、onnxruntime がある場合、`--runtime_dir`引数の指定は不要です。  
`--voicelib_dir`引数、`--runtime_dir`引数は複数回使用可能です。  
API エンドポイントでコアのバージョンを指定する場合は`core_version`引数を指定してください。（未指定の場合は最新のコアが使用されます）

```bash
uv run run.py --voicelib_dir="/path/to/voicevox_core" --runtime_dir="/path/to/libtorch_or_onnx"
```

Mac では、`--runtime_dir`引数の代わりに`DYLD_LIBRARY_PATH`の指定が必要です。

```bash
DYLD_LIBRARY_PATH="/path/to/onnx" uv run run.py --voicelib_dir="/path/to/voicevox_core"
```

##### ユーザーディレクトリに配置する

以下のディレクトリにある音声ライブラリは自動で読み込まれます。

- ビルド版: `<user_data_dir>/voicevox-engine/core_libraries/`
- Python 版: `<user_data_dir>/voicevox-engine-dev/core_libraries/`

`<user_data_dir>`は OS によって異なります。

- Windows: `C:\Users\<username>\AppData\Local\`
- macOS: `/Users/<username>/Library/Application\ Support/`
- Linux: `/home/<username>/.local/share/`

### ビルド

`pyinstaller` を用いたパッケージ化によりローカルでビルドが可能です。  
手順の詳細は [貢献者ガイド#ビルド](./CONTRIBUTING.md#ビルド) を御覧ください。

GitHub を用いる場合、fork したリポジトリで GitHub Actions によるビルドが可能です。  
Actions を ON にし、workflow_dispatch で`build-engine.yml`を起動すればビルドできます。
成果物は Release にアップロードされます。
ビルドに必要な GitHub Actions の設定は [貢献者ガイド#GitHub Actions](./CONTRIBUTING.md#github-actions) を御覧ください。

### テスト・静的解析

`pytest` を用いたテストと各種リンターを用いた静的解析が可能です。  
手順の詳細は [貢献者ガイド#テスト](./CONTRIBUTING.md#テスト), [貢献者ガイド#静的解析](./CONTRIBUTING.md#静的解析) を御覧ください。

### 依存関係

依存関係は `uv` で管理されています。また、導入可能な依存ライブラリにはライセンス上の制約があります。  
詳細は [貢献者ガイド#パッケージ](./CONTRIBUTING.md#パッケージ) を御覧ください。

### マルチエンジン機能に関して

VOICEVOX エディターでは、複数のエンジンを同時に起動することができます。
この機能を利用することで、自作の音声合成エンジンや既存の音声合成エンジンを VOICEVOX エディター上で動かすことが可能です。
詳しくは [MULTIENGINE_GUIDE.md](./MULTIENGINE_GUIDE.md) をご覧ください。

## 事例紹介

**[voicevox-client](https://github.com/voicevox-client) [@voicevox-client](https://github.com/voicevox-client)** ･･･ VOICEVOX ENGINE の各言語向け API ラッパー

## ライセンス

LGPL v3 と、ソースコードの公開が不要な別ライセンスのデュアルライセンスです。
別ライセンスを取得したい場合は、ヒホに求めてください。  
X アカウント: [@hiho_karuta](https://x.com/hiho_karuta)
