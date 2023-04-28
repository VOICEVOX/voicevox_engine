# VOICEVOX ENGINE

[![build](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build.yml)
[![releases](https://img.shields.io/github/v/release/VOICEVOX/voicevox_engine)](https://github.com/VOICEVOX/voicevox_engine/releases)
[![discord](https://img.shields.io/discord/879570910208733277?color=5865f2&label=&logo=discord&logoColor=ffffff)](https://discord.gg/WMwWetrzuh)

[![test](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/VOICEVOX/voicevox_engine/badge.svg)](https://coveralls.io/github/VOICEVOX/voicevox_engine)

[![build-docker](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-docker.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-docker.yml)
[![docker](https://img.shields.io/docker/pulls/voicevox/voicevox_engine)](https://hub.docker.com/r/voicevox/voicevox_engine)

Translation: [JP](./README.md)

This is the engine of [VOICEVOX](https://voicevox.hiroshiba.jp/). It is actually an HTTP server, so you can perform text-to-speech synthesis by sending a request.

(The editor is [VOICEVOX](https://github.com/VOICEVOX/voicevox/), the core is [VOICEVOX CORE](https://github.com/VOICEVOX/voicevox_core/), and the overall structure is detailed in [here](https://github.com/VOICEVOX/voicevox/blob/main/docs/%E5%85%A8%E4%BD%93%E6%A7%8B%E6%88%90.md).)


## Download

Please download the corresponding engine from [here](https://github.com/VOICEVOX/voicevox_engine/releases/latest).

## API Documentation

Please refer to the [API Documentation](https://voicevox.github.io/voicevox_engine/api/).

You can also access the documentation for the running engine by visiting http://127.0.0.1:50021/docs while the VOICEVOX engine or editor is running. The article on [Integration with the VOICEVOX Text-to-Speech Synthesis Engine](./docs/VOICEVOX音声合成エンジンとの連携.md) may also be helpful for future reference.

The character encoding for requests and responses is all UTF-8.

### Sample code for text-to-speech synthesis with an HTTP request

```bash
echo -n "こんにちは、音声合成の世界へようこそ" >text.txt

curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=1"\
    --get --data-urlencode text@text.txt \
    > query.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=1" \
    > audio.wav
```

The generated audio has a sampling rate of 24000Hz, which is slightly unusual, so it may not play back on some audio players.

The value specified for `speaker` is the `style_id` obtained from the `/speakers` endpoint. It is named `speaker` for compatibility purposes.

### Sample Code for Obtaining and Modifying Pronunciation in AquesTalk Notation

The response from `/audio_query` includes the pronunciation determined by the engine in AquesTalk-like notation (which differs from the original notation in some ways). The notation follows the rules below:

- All kana characters are written in katakana.
- Accent phrases are separated by `/` or `、`. If separated by `、`, a silent interval is inserted.
- Placing `_` before a kana character indicates that it is voiceless.
- The accent position is specified by `'`. Each accent phrase must have one accent position specified.
- Adding `？` (full-width) at the end of an accent phrase creates a questioning intonation.

```bash
# Write the text you want to read in UTF-8 to text.txt
echo -n "ディープラーニングは万能薬ではありません" >text.txt

# Send a request to /audio_query with speaker ID and text as query parameters
curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=1" \
    --get --data-urlencode text@text.txt \
    > query.json

# Extract the pronunciation in kana notation from the response and print it
cat query.json | grep -o -E "\"kana\":\".*\""
# Result... "kana":"ディ'イプ/ラ'アニングワ/バンノオヤクデワアリマセ'ン"

# To read it as "ディイプラ'アニングワ/バンノ'オヤクデワ/アリマセ'ン",
# use is_kana=true to obtain the intonation and save it in newphrases.json
echo -n "ディイプラ'アニングワ/バンノ'オヤクデワ/アリマセ'ン" > kana.txt
curl -s \
    -X POST \
    "127.0.0.1:50021/accent_phrases?speaker=1&is_kana=true" \
    --get --data-urlencode text@kana.txt \
    > newphrases.json

# Replace the content of "accent_phrases" in query.json with the content of newphrases.json
cat query.json | sed -e "s/\[{.*}\]/$(cat newphrases.json)/g" > newquery.json

# Send a request to /synthesis with the modified query and speaker ID as query parameters
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @newquery.json \
    "127.0.0.1:50021/synthesis?speaker=1" \
    > audio.wav
```

### About the User Dictionary Feature

You can use the API to reference, add, edit, and delete words in the user dictionary.

#### Reference

You can retrieve a list of user dictionary entries by sending a GET request to `/user_dict`.

```bash
curl -s -X GET "127.0.0.1:50021/user_dict"
```

#### Adding a word

You can add a word to the user dictionary by sending a POST request to `/user_dict_word`. The following parameters are required as URL parameters:

- `surface` (the word to be registered in the dictionary)
- `pronunciation` (the reading in katakana)
- `accent_type` (the accent nucleus position, an integer)

For information about accent nucleus position, please refer to the following article. The part where the number is written as "〇型" is the accent nucleus position.
https://tdmelodic.readthedocs.io/ja/latest/pages/introduction.html

The return value on success is the UUID string assigned to the word.

```bash
surface="test"
pronunciation="テスト"
accent_type="1"

curl -s -X POST "127.0.0.1:50021/user_dict_word" \
    --get \
    --data-urlencode "surface=$surface" \
    --data-urlencode "pronunciation=$pronunciation" \
    --data-urlencode "accent_type=$accent_type"
```

#### Word correction

By sending a PUT request to `/user_dict_word/{word_uuid}`, you can correct a word in the user dictionary. The following are required as URL parameters:

- surface (the word to be registered in the dictionary)
- pronunciation (how to read the word in katakana)
- accent_type (the position of the accent nucleus as an integer)

The word_uuid can be confirmed when adding a word, and it can also be confirmed by referring to the user dictionary. If successful, the return value will be `204 No Content`.

```bash
surface="test2"
pronunciation="テストツー"
accent_type="2"
# Please change word_uuid appropriately depending on your environment
word_uuid="cce59b5f-86ab-42b9-bb75-9fd3407f1e2d"

curl -s -X PUT "127.0.0.1:50021/user_dict_word/$word_uuid" \
    --get \
    --data-urlencode "surface=$surface" \
    --data-urlencode "pronunciation=$pronunciation" \
    --data-urlencode "accent_type=$accent_type"
```

#### Word Deletion

By sending a DELETE request to `/user_dict_word/{word_uuid}`, you can delete a word in the user dictionary.

The word_uuid can be confirmed when adding a word, and it can also be confirmed by referring to the user dictionary. If successful, the return value will be `204 No Content`.

```bash
# Please change word_uuid appropriately depending on your environment
word_uuid="cce59b5f-86ab-42b9-bb75-9fd3407f1e2d"

curl -s -X DELETE "127.0.0.1:50021/user_dict_word/$word_uuid"
```

### About the Preset Feature

You can use presets for speakers, speech rate, and more by editing `presets.yaml`.

```bash
echo -n "プリセットをうまく活用すれば、サードパーティ間で同じ設定を使うことができます" >text.txt

# Get preset information
curl -s -X GET "127.0.0.1:50021/presets" > presets.json

preset_id=$(cat presets.json | sed -r 's/^.+"id"\:\s?([0-9]+?).+$/\1/g')
style_id=$(cat presets.json | sed -r 's/^.+"style_id"\:\s?([0-9]+?).+$/\1/g')

# Get AudioQuery
curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query_from_preset?preset_id=$preset_id"\
    --get --data-urlencode text@text.txt \
    > query.json

# Text-to-speech synthesis
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=$style_id" \
    > audio.wav
```

- `speaker_uuid` can be confirmed by `/speakers`.
- `id` must not be duplicated.
- If you rewrite the file after the engine has started, the changes will be reflected in the engine.

### Sample code for morphing between two speakers

The `/synthesis_morphing` endpoint generates a morphed audio by using two speakers' synthesized audio.

```bash
echo -n "モーフィングを利用することで、２つの声を混ぜることができます。" > text.txt

curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=0"\
    --get --data-urlencode text@text.txt \
    > query.json

# Synthesized audio with the first speaker
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=0" \
    > audio.wav

export MORPH_RATE=0.5

# It takes time because it includes speech synthesis for two speakers and audio analysis with WORLD
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis_morphing?base_speaker=0&target_speaker=1&morph_rate=$MORPH_RATE" \
    > audio.wav

export MORPH_RATE=0.9

# When query, base_speaker, and target_speaker are the same, the cache is used, so it can be generated relatively quickly.
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis_morphing?base_speaker=0&target_speaker=1&morph_rate=$MORPH_RATE" \
    > audio.wav
```

### Sample code to retrieve additional information about a speaker

This code retrieves the `portrait.png` file from the additional information. (It parses the JSON using [jq](https://stedolan.github.io/jq/).)

```bash
curl -s -X GET "127.0.0.1:50021/speaker_info?speaker_uuid=7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff" \
    | jq  -r ".portrait" \
    | base64 -d \
    > portrait.png
```

### Cancellable Speech Synthesis

In `/cancellable_synthesis`, computation resources are released immediately when the communication is interrupted. (In `/synthesis`, the calculation for speech synthesis continues even if the communication is interrupted.) This API is an experimental feature and needs to be enabled by specifying the argument `--enable_cancellable_synthesis` when starting the engine. The necessary parameters for speech synthesis are the same as those for `/synthesis`.

### CORS settings

In VOICEVOX, requests from origins other than `localhost`, `127.0.0.1`, `app://`, and no origin are not accepted for security reasons. Therefore, there is a possibility that responses from some third-party applications may not be received.

To avoid this, VOICEVOX provides a UI that can be used to configure the CORS settings from the engine.

#### Setting Method

1. Access to <http://127.0.0.1:50021/setting>.
2. Change or add settings according to the application you use.
3. Press the Save button to confirm the changes.
4. Restart the engine to apply the changes. Restart if necessary.

### Other arguments

You can specify arguments when starting the engine. For more information, please check the help with the `-h` argument.

```bash
$ python run.py -h

usage: run.py [-h] [--host HOST] [--port PORT] [--use_gpu] [--voicevox_dir VOICEVOX_DIR] [--voicelib_dir VOICELIB_DIR] [--runtime_dir RUNTIME_DIR] [--enable_mock] [--enable_cancellable_synthesis] [--init_processes INIT_PROCESSES] [--load_all_models]
              [--cpu_num_threads CPU_NUM_THREADS] [--output_log_utf8] [--cors_policy_mode {CorsPolicyMode.all,CorsPolicyMode.localapps}] [--allow_origin [ALLOW_ORIGIN ...]] [--setting_file SETTING_FILE]

This is the engine for VOICEVOX.

options:
  -h, --help            show this help message and exit
  --host HOST           The host address to accept connections.
  --port PORT           The port number to accept connections.
  --use_gpu             Specify to use the GPU for speech synthesis.
  --voicevox_dir VOICEVOX_DIR
                        The directory path of VOICEVOX.
  --voicelib_dir VOICELIB_DIR
                        The directory path of VOICEVOX CORE.
  --runtime_dir RUNTIME_DIR
                        The directory path of the libraries used in VOICEVOX CORE.
  --enable_mock         Specify to perform speech synthesis with a mock instead of VOICEVOX CORE.
  --enable_cancellable_synthesis
                        Specify to enable the ability to cancel speech synthesis midway.
  --init_processes INIT_PROCESSES
                        The number of processes generated when initializing the cancellable_synthesis feature.
  --load_all_models     Specify to load all speech synthesis models at startup.
  --cpu_num_threads CPU_NUM_THREADS
                        The number of threads used for speech synthesis. If not specified, the value of the environment variable VV_CPU_NUM_THREADS will be used instead. If VV_CPU_NUM_THREADS is not a numeric string or an empty string, the program will exit with an error.
  --output_log_utf8     Specify to output logs in UTF-8. If not specified, the value of the environment variable VV_OUTPUT_LOG_UTF8 will be used instead. If the value of VV_OUTPUT_LOG_UTF8 is 1, UTF-8 will be used. If the value is 0 or an empty string, or if the variable is not set, the output encoding will be determined automatically by the environment.
  --cors_policy_mode {CorsPolicyMode.all,CorsPolicyMode.localapps}
                        The permission mode for CORS. You can specify all or localapps. all allows everything. localapps limits the cross-origin resource sharing policy to app:// and localhost-related origins. Other origins can be added with the allow_origin option. The default is localapps.
  --allow_origin [ALLOW_ORIGIN ...]
                        Specify the allowed origins. Multiple origins can be specified by separating them with spaces.
  --setting_file SETTING_FILE
                        Specify the settings file.
```

## Update

Please delete all files in the engine directory and replace them with the new ones.

## Docker Image

### CPU

```bash
docker pull voicevox/voicevox_engine:cpu-ubuntu20.04-latest
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

### GPU

```bash
docker pull voicevox/voicevox_engine:nvidia-ubuntu20.04-latest
docker run --rm --gpus all -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:nvidia-ubuntu20.04-latest
```

#### Troubleshooting

When using the GPU version, errors may occur depending on the environment. In that case, adding `--runtime=nvidia` to `docker run` may solve the problem.

## For contributors

When creating a pull request to solve an issue, please avoid working on the same issue as someone else by letting them know that you have started working on the issue or by creating a draft pull request first.

We discuss development and chat on the [VOICEVOX unofficial Discord server](https://discord.gg/WMwWetrzuh). Please feel free to join us.

## Environment setup

It is developed using `Python 3.11.3`. To install, you need a C/C++ compiler and CMake for each OS.

```bash
# Install required libraries for development
python -m pip install -r requirements-dev.txt -r requirements-test.txt

# If you just want to run it for now, use this instead
python -m pip install -r requirements.txt
```

## Execution

Please confirm the details of the command line arguments with the following command.

```bash
python run.py --help
```

```bash
# Start the server with VOICEVOX product version
VOICEVOX_DIR="C:/path/to/voicevox" # Path to the VOICEVOX product version directory
python run.py --voicevox_dir=$VOICEVOX_DIR
```

<!--
Uncomment the following section when a replaceable voice library or its specifications are released.
```bash
# Replace the voice library
VOICELIB_DIR="C:/path/to/your/tts-model"
python run.py --voicevox_dir=$VOICEVOX_DIR --voicelib_dir=$VOICELIB_DIR
```
-->

```bash
# Start the server with mock
python run.py --enable_mock
```

```bash
# Change the log to UTF8
python run.py --output_log_utf8
# Or use VV_OUTPUT_LOG_UTF8=1 python run.py
```

### Specifying the number of CPU threads

If the number of CPU threads is not specified, half of the logical cores or physical cores will be used. (This is about half of the overall processing power on most CPUs.)  
If you want to adjust the processing power used by the engine, for example, when running on an IaaS or dedicated server, you can do so by specifying the number of CPU threads.

- Specify with a command-line argument

  ```bash
  python run.py --voicevox_dir=$VOICEVOX_DIR --cpu_num_threads=4
  ```

- Specify with an environment variable

  ```bash
  export VV_CPU_NUM_THREADS=4
  python run.py --voicevox_dir=$VOICEVOX_DIR
  ```

### Using a previous version of the Core

It is possible to use a Core version from 0.5.4 or later in VOICEVOX.  
Support for libtorch-based Core on Mac is not available.

#### Specifying the previous binary

If you specify the directory of the VOICEVOX product or the compiled engine with the `--voicevox_dir` argument, the Core of that version will be used.

```bash
python run.py --voicevox_dir="/path/to/voicevox"
```

On Mac, `DYLD_LIBRARY_PATH` needs to be specified.

```bash
DYLD_LIBRARY_PATH="/path/to/voicevox" python run.py --voicevox_dir="/path/to/voicevox"
```

#### Specifying the audio library directly

Specify the directory where the [VOICEVOX Core zip file](https://github.com/VOICEVOX/voicevox_core/releases) is extracted using the `--voicelib_dir` argument.  
Also, depending on the version of the core, specify the directories of [libtorch](https://pytorch.org/) or [onnxruntime](https://github.com/microsoft/onnxruntime) using the `--runtime_dir` argument.  
However, if libtorch or onnxruntime is on the system's search path, the `--runtime_dir` argument is not necessary.  
The `--voicelib_dir` and `--runtime_dir` arguments can be used multiple times.  
If you want to specify the version of the core in the API endpoint, use the `core_version` argument. (If not specified, the latest core will be used.)

```bash
python run.py --voicelib_dir="/path/to/voicevox_core" --runtime_dir="/path/to/libtorch_or_onnx"
```

On Mac, instead of the `--runtime_dir` argument, specify the `DYLD_LIBRARY_PATH`.

```bash
DYLD_LIBRARY_PATH="/path/to/onnx" python run.py --voicelib_dir="/path/to/voicevox_core"
```

## Code Format

In this software, you can use a static analysis tool to check the code format before pushing it to remote. To use it, you need to install the required libraries for development and run the following command. It is recommended to use it when creating a pull request.

```bash
pre-commit install -t pre-push
```

If an error occurs, you can fix it with the following command. However, please note that it may not be possible to fix it completely.

```bash
pysen run format lint
```

## Typo Check

We use [typos](https://github.com/crate-ci/typos) to check for typos. After installing [typos](https://github.com/crate-ci/typos#install), you can run the following command to check for typos:

```bash
typos
```

If there are files that should be excluded from the check or if there are false positives, please edit `_typos.toml` according to the [configuration file instructions](https://github.com/crate-ci/typos#false-positives).

## API Documentation Confirmation

The [API documentation](https://voicevox.github.io/voicevox_engine/api/) (actually `docs/api/index.html`) is automatically updated.  
You can manually create the API documentation with the following command:

```bash
python make_docs.py
```

## Build

The product built using this method will differ from the one released in the official release. In addition, libraries such as cuDNN, CUDA, and DirectML are required to use it with a GPU.

```bash
python -m pip install -r requirements-dev.txt

OUTPUT_LICENSE_JSON_PATH=licenses.json \
bash build_util/create_venv_and_generate_licenses.bash

# Building is possible even without specifying LIBCORE_PATH and LIBONNXRUNTIME_PATH
LIBCORE_PATH="/path/to/libcore" \
    LIBONNXRUNTIME_PATH="/path/to/libonnxruntime" \
    pyinstaller --noconfirm run.spec
```

## Dependency

### Updating

We use [Poetry](https://python-poetry.org/) to manage dependency versions. You can use the following commands:

```bash
# To add a package
poetry add `package-name`
poetry add --group dev `package-name` # To add a development dependency
poetry add --group test `package-name` # To add a testing dependency

# To update a package
poetry update `package-name`
poetry update # To update all packages

# Updating requirements.txt
poetry export --without-hashes -o requirements.txt # If you update this file, you also need to update the following three files
poetry export --without-hashes --with dev -o requirements-dev.txt
poetry export --without-hashes --with test -o requirements-test.txt
poetry export --without-hashes --with license -o requirements-license.txt
```

### License

Dependency libraries must have a license that allows "linking and integrating at build time, but not requiring the core code to be made public". The acceptability of major licenses is as follows:

- MIT/Apache/BSD-3: OK
- LGPL: OK (because it is dynamically separated from the core)
- GPL: NG (because all related code must be made public)

## Updating the user dictionary

You can compile the user dictionary for OpenJTalk with the following command:

```bash
python -c "import pyopenjtalk; pyopenjtalk.create_user_dict('default.csv','user.dic')"
```

Translation:

## About Multi-Engine Function

With the VOICEVOX Editor, you can start multiple engines at the same time. By using this feature, it is possible to run your own speech synthesis engine or an existing speech synthesis engine on the VOICEVOX Editor.

<img src="./docs/res/multi-engine-diagram.svg" width="320">

<details>

### Mechanism of Multi-Engine Function

The multi-engine function is achieved by starting multiple engines' Web APIs that conform to the VOICEVOX API on separate ports and handling them uniformly. The editor starts each engine via an execution binary, associates it with an EngineID, and individually manages settings and status.

### How to Support Multi-Engine Function

It is possible to support by creating an execution binary that starts an engine that conforms to the VOICEVOX API. Forking the VOICEVOX ENGINE repository and modifying some features is easy.

The three points that need to be modified are engine information, character information, and speech synthesis.

The engine information is managed in the engine manifest (`engine_manifest.json`). Please modify the information in the manifest file as necessary. Depending on the speech synthesis method, there may be cases where it is not possible to have the same functions as VOICEVOX, such as morphing function. In that case, please modify the information in `supported_features` in the manifest file as appropriate.

Character information is managed in files in the `speaker_info` directory. Dummy icons, etc., are provided, so please modify them as appropriate.

Speech synthesis is performed in `voicevox_engine/synthesis_engine/synthesis_engine.py`. Speech synthesis with the VOICEVOX API is achieved by creating an initial value of the audio synthesis query `AudioQuery` on the engine side and returning it to the user. The engine synthesizes audio according to the query after the user edits it as necessary. Query creation is done at the `/audio_query` endpoint, and speech synthesis is done at the `/synthesis` endpoint. If you support at least these two endpoints, you are considered to comply with the VOICEVOX API.

### Distribution Method for Multi-Engine Supported Engines

It is recommended to distribute as a VVPP file. VVPP stands for "VOICEVOX Plugin Package," and its contents are a zip file of a directory that includes the built engine, etc. If the extension is changed to `.vvpp`, it can be installed in the VOICEVOX Editor by double-clicking.

On the editor side, after unpacking the received VVPP file into a zip on the local disk, it searches for files according to `engine_manifest.json` at the root. If you cannot load it properly into the VOICEVOX Editor, please refer to the editor error log.

It is also possible to distribute the `xxx.vvpp` file as a split file with a sequential number attached, such as `xxx.0.vvppp`. This is useful when the file size is large and distribution is difficult.

</details>

## GitHub Actions

### Variables

| name               | description                                                             |
| :----------------- | :---------------------------------------------------------------------- |
| DOCKERHUB_USERNAME | Docker Hub username                                                     |

### Secrets

| name               | description                                                             |
| :----------------- | :---------------------------------------------------------------------- |
| DOCKERHUB_TOKEN    | [Docker Hub Access Token](https://hub.docker.com/settings/security) |

## Use Case Introduction

**[voicevox-client](https://github.com/tuna2134/voicevox-client) [@tuna2134](https://github.com/tuna2134)** ･･･ Python wrapper for VOICEVOX ENGINE

## License

Dual-licensed under LGPL v3 and another license that does not require source code to be published. If you want to obtain another license, please contact Hiho (twitter: @hiho_karuta).
