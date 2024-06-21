# ResourceManagerの仕様について

一部のリソースファイルはURLとして返します。  
ファイルの内容が変わってもURLが同じ場合、キャッシュが働いて新しいリソースを取得できない可能性があります。  
これを防ぐためハッシュを使用してリソースの変更の度にURLを変更します。

ResourceManagerはファイルとハッシュを管理します。  
filemap.jsonは事前に生成したハッシュとファイルの関連付けを行います。  
generate_filemap.pyはfilemap.pyの作成を行います。

## ResourceManager

初期化時に`create_filemap_if_not_exist`を`True`にすると`filemap.json`がないディレクトリの登録ができます。  
登録されるリソースは`filemap.json`にあるものに限ります。  
`filemap.json`がない場合ディレクトリ内のすべてのファイルが登録されます。

細かい仕様はResourceManagerのドキュメントと実装を確認してください。

## filemap.json

キーは登録するファイルパスを登録するディレクトリを基準にした相対パスです。  
パス区切り文字は互換性のため`/`である必要があります。

値は登録するファイルを一意に識別できるハッシュ等の文字列です。  
`generate_filemap.py`はsha256ハッシュを生成します。

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
  "dir_2/samples/登録ファイル.wav": "HASH-4",
}
```

## generate_filemap.py

`filemap.json`を生成するためのスクリプトです。  
デフォルトではpngファイルとwavファイルのみを登録します。

### 例

```bash
python tools/generate_filemap.py --target_dir resources/character_info
```

pngとwavに加えてjpgファイルを登録する例
```bash
python tools/generate_filemap.py --target_dir resources/character_info \
    --target_suffix png --target_suffix wav --target_suffix jpg
```
