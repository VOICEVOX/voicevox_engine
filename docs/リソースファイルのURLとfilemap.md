# リソースファイルの URL の仕様について

VOICEVOX ENGINE では一部のリソースファイルを URL として返します。  
リソースファイルを更新しても URL が同じ場合、キャッシュが働いて新しいリソースを取得できないことがあります。  
これを防ぐためにリソースファイルのハッシュ値を URL に含め、リソースの変更の度に URL が変わるようにしています。

ResourceManager はファイルとハッシュの対応を管理します。  
filemap.json はファイルとハッシュを予め対応付けたファイルです。  
generate_filemap.py は filemap.json の作成を行います。

## ResourceManager

`filemap.json`にあるリソースファイルを登録できます。
初期化時に`create_filemap_if_not_exist`を`True`にすると`filemap.json`がないディレクトリの登録ができます。

細かい仕様は ResourceManager のドキュメントと実装を確認してください。

## filemap.json

`filemap.json`のキーは、登録するディレクトリからリソースファイルへの相対パスです。  
パス区切り文字は互換性のため`/`である必要があります。

値は登録するファイルを一意に識別できるハッシュ等の文字列です。  
`generate_filemap.py`は sha256 ハッシュを生成します。

### 例

#### デイレクトリ構造

```
登録ディレクトリ/
├── filemap.json
├── dir_1/
│   ├── 登録ファイル.png
│   ├── samples/
│   │   └── 登録ファイル.wav
│   └── 非登録ファイル1.txt
└── dir_2/
    ├── 登録ファイル.png
    ├── samples/
    │   └── 登録ファイル.wav
    └── 非登録ファイル1.txt
```

#### filemap.json

```json
{
  "dir_1/登録ファイル.png": "HASH-1",
  "dir_1/samples/登録ファイル.wav": "HASH-2",
  "dir_2/登録ファイル.png": "HASH-3",
  "dir_2/samples/登録ファイル.wav": "HASH-4"
}
```

## generate_filemap.py

`filemap.json`を生成するためのスクリプトです。  
デフォルトでは png ファイルと wav ファイルのみを登録します。

### 例

```bash
python tools/generate_filemap.py --target_dir resources/character_info
```

png と wav に加えて jpg ファイルを登録する例

```bash
python tools/generate_filemap.py --target_dir resources/character_info \
    --target_suffix png --target_suffix wav --target_suffix jpg
```
