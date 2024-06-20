# ResourceManagerの仕様について

## ResourceManager

### 初期化

`create_filemap_if_not_exist`に`True`を渡すことによって登録するディレクトリに`filemap.json`が存在しないディレクトリを登録可能にします。  
これは開発時を想定したものです。

### リソースの登録

`register_dir(resource_dir)`でディレクトリ内のリソースを登録します。  
登録されるリソースは`filemap.json`にあるものに限ります。

`filemap.json`がない場合
- `create_filemap_if_not_exist`が`False`  
`ResourceManagerError`が発生します。

- `create_filemap_if_not_exist`が`True`  
ディレクトリ内のすべてのファイルが登録されます。

## filemap.json

### 仕様

キーは登録するファイルパスを登録するディレクトリを基準にした相対パスです。

値は登録するファイルを一意に識別できるハッシュ等の文字列です。  
`generate_filemap.py`はsha256ハッシュを生成します。

### 例

#### デイレクトリ構造

```
├── ...
├── resources/
│   └── 登録ディレクトリ/
│       ├── filemap.json
│       ├── dir_1/
│       │   ├── 登録ファイル.png
│       │   ├── samples/
│       │   │   └── 登録ファイル.wav
│       │   └── 非登録ファイル1.txt
│       └── dir_2/
│           ├── 登録ファイル.png
│           ├── samples/
│           │   └── 登録ファイル.wav
│           └── 非登録ファイル1.txt
├── ...
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
python build_util/generate_filemap.py --target_dir resources/character_info
```

pngとwavに加えてjpgファイルを登録する例
```bash
python build_util/generate_filemap.py --target_dir resources/character_info \
    --target_suffix png --target_suffix wav --target_suffix jpg
```
