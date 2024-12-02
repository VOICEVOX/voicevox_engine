# Specifications for Resource File URLs

VOICEVOX ENGINE returns some resource files as URLs.
If the URL remains the same even after updating a resource file, caching might prevent fetching the new resource.
To prevent this, we include the hash value of the resource file in the URL, ensuring the URL changes with each resource modification.

ResourceManager manages the correspondence between files and their hashes.
filemap.json is a file that pre-maps files to their hashes.
generate_filemap.py creates the filemap.json.

## ResourceManager

Resource files listed in `filemap.json` can be registered.
If `create_filemap_if_not_exist` is set to `True` during initialization, directories without `filemap.json` can be registered.

For detailed specifications, please refer to the ResourceManager documentation and implementation.

## filemap.json

The keys in `filemap.json` are relative paths from the registration directory to the resource files.
For compatibility, the path separator must be `/`.

The values are strings, such as hashes, that uniquely identify the registered files.
`generate_filemap.py` generates sha256 hashes.

### Example

#### Directory Structure

```
Registration Directory/
├── filemap.json
├── dir_1/
│   ├── registered_file.png
│   ├── samples/
│   │   └── registered_file.wav
│   └── unregistered_file1.txt
└── dir_2/
    ├── registered_file.png
    ├── samples/
    │   └── registered_file.wav
    └── unregistered_file1.txt
```

#### filemap.json

```json
{
  "dir_1/registered_file.png": "HASH-1",
  "dir_1/samples/registered_file.wav": "HASH-2",
  "dir_2/registered_file.png": "HASH-3",
  "dir_2/samples/registered_file.wav": "HASH-4"
}
```

## generate_filemap.py

This script generates `filemap.json`.
By default, it only registers png and wav files.

### Example

```bash
python tools/generate_filemap.py --target_dir resources/character_info
```

Example of registering jpg files in addition to png and wav

```bash
python tools/generate_filemap.py --target_dir resources/character_info \
    --target_suffix png --target_suffix wav --target_suffix jpg
```
