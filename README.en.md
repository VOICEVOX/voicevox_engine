# VOICEVOX ENGINE

[![build](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-package.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-package.yml)
[![releases](https://img.shields.io/github/v/release/VOICEVOX/voicevox_engine)](https://github.com/VOICEVOX/voicevox_engine/releases)
[![discord](https://img.shields.io/discord/879570910208733277?color=5865f2&label=&logo=discord&logoColor=ffffff)](https://discord.gg/WMwWetrzuh)

[![test](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/VOICEVOX/voicevox_engine/badge.svg)](https://coveralls.io/github/VOICEVOX/voicevox_engine)

[![build-docker](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-container.yml/badge.svg)](https://github.com/VOICEVOX/voicevox_engine/actions/workflows/build-engine-container.yml)
[![docker](https://img.shields.io/docker/pulls/voicevox/voicevox_engine)](https://hub.docker.com/r/voicevox/voicevox_engine)

[Japanese](./README.md)

This is the engine for [VOICEVOX](https://voicevox.hiroshiba.jp/).  
It's essentially an HTTP server, so you can perform text-to-speech synthesis by sending requests.

(The editor is [VOICEVOX](https://github.com/VOICEVOX/voicevox/),
the core is [VOICEVOX CORE](https://github.com/VOICEVOX/voicevox_core/),
and the overall structure is detailed [here](https://github.com/VOICEVOX/voicevox/blob/main/docs/%E5%85%A8%E4%BD%93%E6%A7%8B%E6%88%90.md).)

## Table of Contents

Here are guides tailored to your specific needs:

- [User Guide](#user-guide): For those who want to perform text-to-speech synthesis
- [Contributor Guide](#contributor-guide): For those who want to contribute to the project
- [Developer Guide](#developer-guide): For those who want to utilize the code

## User Guide

### Download

Please download the corresponding engine from [here](https://github.com/VOICEVOX/voicevox_engine/releases/latest).

### API Documentation

Please refer to the [API Documentation](https://voicevox.github.io/voicevox_engine/api/).

You can also access the documentation for the running engine by visiting http://127.0.0.1:50021/docs while the VOICEVOX engine or editor is running.  
For future plans and other information, you may find [Collaboration with VOICEVOX Text-to-Speech Engine](./docs/Integration_with_VOICEVOX_Speech_Synthesis_Engine.en.md) helpful.

### Docker Image

#### CPU

```bash
docker pull voicevox/voicevox_engine:cpu-ubuntu20.04-latest
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

#### GPU

```bash
docker pull voicevox/voicevox_engine:nvidia-ubuntu20.04-latest
docker run --rm --gpus all -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:nvidia-ubuntu20.04-latest
```

##### Troubleshooting

When using the GPU version, errors may occur depending on the environment. In such cases, adding `--runtime=nvidia` to the `docker run` command may resolve the issue.

### Sample Code for Text-to-Speech Synthesis via HTTP Request

```bash
echo -n "Hello, welcome to the world of speech synthesis" >text.txt

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

The generated audio has a somewhat unusual sampling rate of 24000Hz, which may not be playable on some audio players.

The value specified for `speaker` is the `style_id` obtained from the `/speakers` endpoint. It's named `speaker` for compatibility reasons.

### Sample Code for Adjusting Speech

You can adjust the speech by editing the parameters of the query for speech synthesis obtained from `/audio_query`.

For example, let's try to increase the speech speed by 1.5 times.

```bash
echo -n "Hello, welcome to the world of speech synthesis" >text.txt

curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=1" \
    --get --data-urlencode text@text.txt \
    > query.json

# Use sed to change the value of speedScale to 1.5
sed -i -r 's/"speedScale":[0-9.]+/"speedScale":1.5/' query.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=1" \
    > audio_fast.wav
```

### Retrieving and Modifying Pronunciation with AquesTalk-like Notation

#### AquesTalk-like Notation

<!-- NOTE: This section is currently used as a static link, so it's better not to change it (voicevox_engine#816) -->

"**AquesTalk-like Notation**" is a notation that specifies pronunciation using only katakana and symbols. It differs slightly from [the original AquesTalk notation](https://www.a-quest.com/archive/manual/siyo_onseikigou.pdf).  
AquesTalk-like Notation follows these rules:

- All kana are written in katakana
- Accent phrases are separated by `/` or `、`. A silent interval is inserted only when separated by `、`.
- Placing `_` before a kana makes that kana unvoiced
- Accent position is specified with `'`. Each accent phrase must have one accent position specified.
- Adding `？` (full-width) at the end of an accent phrase allows for interrogative pronunciation

#### Sample Code for AquesTalk-like Notation

The response from `/audio_query` includes the pronunciation determined by the engine, described in [AquesTalk-like Notation](#aquestalk-like-notation).  
By modifying this, you can control the reading and accent of the speech.

```bash
# Write the text you want to be read in utf-8 to text.txt
echo -n "Deep learning is not a panacea" >text.txt

curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=1" \
    --get --data-urlencode text@text.txt \
    > query.json

cat query.json | grep -o -E "\"kana\":\".*\""
# Result... "kana":"ディ'イプ/ラ'アニングワ/パンノオヤクデワアリマセ'ン"

# We want it to be read as "ディイプラ'アニングワ/パンノ'オヤクデワ/アリマセ'ン", so
# Get the intonation with is_kana=true and save it to newphrases.json
echo -n "ディイプラ'アニングワ/パンノ'オヤクデワ/アリマセ'ン" > kana.txt
curl -s \
    -X POST \
    "127.0.0.1:50021/accent_phrases?speaker=1&is_kana=true" \
    --get --data-urlencode text@kana.txt \
    > newphrases.json

# Replace the content of "accent_phrases" in query.json with the content of newphrases.json
cat query.json | sed -e "s/\[{.*}\]/$(cat newphrases.json)/g" > newquery.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @newquery.json \
    "127.0.0.1:50021/synthesis?speaker=1" \
    > audio.wav
```

### User Dictionary Feature

You can reference, add, edit, and delete words in the user dictionary via the API.

#### Reference

You can get a list of the user dictionary by sending a GET request to `/user_dict`.

```bash
curl -s -X GET "127.0.0.1:50021/user_dict"
```

#### Adding Words

You can add words to the user dictionary by sending a POST request to `/user_dict_word`.
The following URL parameters are required:

- surface (the word to be registered in the dictionary)
- pronunciation (katakana reading)
- accent_type (accent nucleus position, integer)

For the accent nucleus position, this text might be helpful.
The number part that is marked with ○ is the accent nucleus position.
https://tdmelodic.readthedocs.io/ja/latest/pages/introduction.html

If successful, the return value will be a string of the UUID assigned to the word.

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

#### Editing Words

You can edit words in the user dictionary by sending a PUT request to `/user_dict_word/{word_uuid}`.
The following URL parameters are required:

- surface (the word to be registered in the dictionary)
- pronunciation (katakana reading)
- accent_type (accent nucleus position, integer)

The word_uuid can be confirmed when adding a word or by referencing the user dictionary.
If successful, the return value will be `204 No Content`.

```bash
surface="test2"
pronunciation="テストツー"
accent_type="2"
# Please replace word_uuid according to your environment
word_uuid="cce59b5f-86ab-42b9-bb75-9fd3407f1e2d"

curl -s -X PUT "127.0.0.1:50021/user_dict_word/$word_uuid" \
    --get \
    --data-urlencode "surface=$surface" \
    --data-urlencode "pronunciation=$pronunciation" \
    --data-urlencode "accent_type=$accent_type"
```

#### Deleting Words

You can delete words from the user dictionary by sending a DELETE request to `/user_dict_word/{word_uuid}`.

The word_uuid can be confirmed when adding a word or by referencing the user dictionary.
If successful, the return value will be `204 No Content`.

```bash
# Please replace word_uuid according to your environment
word_uuid="cce59b5f-86ab-42b9-bb75-9fd3407f1e2d"

curl -s -X DELETE "127.0.0.1:50021/user_dict_word/$word_uuid"
```

#### Importing & Exporting Dictionary

You can import and export the user dictionary in the "User Dictionary Export & Import" section of the engine's [settings page](http://127.0.0.1:50021/setting).

You can also import and export the user dictionary via API.
Use `POST /import_user_dict` for importing and `GET /user_dict` for exporting.
For details on arguments, etc., please refer to the API documentation.

### About Preset Feature

You can use presets for characters, speech speed, etc. by editing `presets.yaml` in the user directory.

```bash
echo -n "By effectively utilizing presets, third parties can use the same settings" >text.txt

# Get preset information
curl -s -X GET "127.0.0.1:50021/presets" > presets.json

preset_id=$(cat presets.json | sed -r 's/^.+"id"\:\s?([0-9]+?).+$/\1/g')
style_id=$(cat presets.json | sed -r 's/^.+"style_id"\:\s?([0-9]+?).+$/\1/g')

# Get query for voice synthesis
curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query_from_preset?preset_id=$preset_id"\
    --get --data-urlencode text@text.txt \
    > query.json

# Voice synthesis
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=$style_id" \
    > audio.wav
```

- `speaker_uuid` can be confirmed with `/speakers`
- `id` must not be duplicated
- Changes to the file will be reflected in the engine after the engine is started

### Sample Code for Morphing with 2 Types of Styles

`/synthesis_morphing` generates morphed audio based on voices synthesized in two different styles.

```bash
echo -n "By using morphing, you can mix two types of voices." > text.txt

curl -s \
    -X POST \
    "127.0.0.1:50021/audio_query?speaker=8"\
    --get --data-urlencode text@text.txt \
    > query.json

# Synthesis result in the original style
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis?speaker=8" \
    > audio.wav

export MORPH_RATE=0.5

# Note that it takes time because it involves voice synthesis for two styles + voice analysis by WORLD
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis_morphing?base_speaker=8&target_speaker=10&morph_rate=$MORPH_RATE" \
    > audio.wav

export MORPH_RATE=0.9

# If query, base_speaker, and target_speaker are the same, cache is used, so it's generated relatively quickly
curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/synthesis_morphing?base_speaker=8&target_speaker=10&morph_rate=$MORPH_RATE" \
    > audio.wav
```

### Sample Code for Retrieving Additional Character Information

This code retrieves portrait.png from the additional information.  
(Using [jq](https://stedolan.github.io/jq/) to parse JSON.)

```bash
curl -s -X GET "127.0.0.1:50021/speaker_info?speaker_uuid=7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff" \
    | jq  -r ".portrait" \
    | base64 -d \
    > portrait.png
```

### Cancellable Voice Synthesis

`/cancellable_synthesis` immediately releases computational resources when the connection is cut.  
(With `/synthesis`, voice synthesis calculation continues to the end even if the connection is cut.)  
This API is an experimental feature and is not enabled unless the `--enable_cancellable_synthesis` argument is specified when starting the engine.  
The parameters required for voice synthesis are the same as for `/synthesis`.

### Sample Code for Song Synthesis via HTTP Request

```bash
echo -n '{
  "notes": [
    { "key": null, "frame_length": 15, "lyric": "" },
    { "key": 60, "frame_length": 45, "lyric": "Do" },
    { "key": 62, "frame_length": 45, "lyric": "Re" },
    { "key": 64, "frame_length": 45, "lyric": "Mi" },
    { "key": null, "frame_length": 15, "lyric": "" }
  ]
}' > score.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @score.json \
    "127.0.0.1:50021/sing_frame_audio_query?speaker=6000" \
    > query.json

curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    -d @query.json \
    "127.0.0.1:50021/frame_synthesis?speaker=3001" \
    > audio.wav
```

The `key` in the score is the MIDI number.  
`lyric` is the lyrics, and any string can be specified, but some engines may return an error for strings other than one mora in hiragana or katakana.  
The default frame rate is 93.75Hz, which can be obtained from `frame_rate` in the engine manifest.  
The first note must be silent.

The `speaker` that can be specified in `/sing_frame_audio_query` is the `style_id` of styles with type `sing` or `singing_teacher` that can be obtained from `/singers`.  
The `speaker` that can be specified in `/frame_synthesis` is the `style_id` of styles with type `frame_decode` that can be obtained from `/singers`.  
The argument is named `speaker` for consistency with other APIs.

It's also possible to specify different styles for `/sing_frame_audio_query` and `/frame_synthesis`.

### CORS Settings

For security protection, VOICEVOX is set to only accept requests from `localhost`, `127.0.0.1`, `app://`, or no Origin.
Therefore, responses may not be received from some third-party applications.  
As a workaround, we provide a UI that can be configured from the engine.

#### Configuration Method

1. Access <http://127.0.0.1:50021/setting>.
2. Change or add settings according to the application you're using.
3. Press the save button to confirm the changes.
4. Restarting the engine is necessary to apply the settings. Please restart as needed.

### Disabling APIs that Modify Data

By specifying the runtime argument `--disable_mutable_api` or setting the environment variable `VV_DISABLE_MUTABLE_API=1`, you can disable APIs that modify engine settings, dictionaries, etc.

### Character Encoding

The character encoding for all requests and responses is UTF-8.

### Other Arguments

Arguments can be specified when starting the engine. For more details, check the help with the `-h` argument.

```bash
$ python run.py -h

usage: run.py [-h] [--host HOST] [--port PORT] [--use_gpu] [--voicevox_dir VOICEVOX_DIR] [--voicelib_dir VOICELIB_DIR] [--runtime_dir RUNTIME_DIR] [--enable_mock] [--enable_cancellable_synthesis]
              [--init_processes INIT_PROCESSES] [--load_all_models] [--cpu_num_threads CPU_NUM_THREADS] [--output_log_utf8] [--cors_policy_mode {CorsPolicyMode.all,CorsPolicyMode.localapps}]
              [--allow_origin [ALLOW_ORIGIN ...]] [--setting_file SETTING_FILE] [--preset_file PRESET_FILE] [--disable_mutable_api]

This is the engine for VOICEVOX.

options:
  -h, --help            show this help message and exit
  --host HOST           The host address to accept connections.
  --port PORT           The port number to accept connections.
  --use_gpu             Enables voice synthesis using GPU.
  --voicevox_dir VOICEVOX_DIR
                        The directory path for VOICEVOX.
  --voicelib_dir VOICELIB_DIR
                        The directory path for VOICEVOX CORE.
  --runtime_dir RUNTIME_DIR
                        The directory path for libraries used by VOICEVOX CORE.
  --enable_mock         Performs voice synthesis with a mock without using VOICEVOX CORE.
  --enable_cancellable_synthesis
                        Enables cancellation of voice synthesis midway.
  --init_processes INIT_PROCESSES
                        The number of processes to generate during initialization of the cancellable_synthesis feature.
  --load_all_models     Loads all voice synthesis models at startup.
  --cpu_num_threads CPU_NUM_THREADS
                        The number of threads for voice synthesis. If not specified, the value of the environment variable VV_CPU_NUM_THREADS is used instead. If VV_CPU_NUM_THREADS is not empty and not a number, it will exit with an error.
  --output_log_utf8     Outputs logs in UTF-8. If not specified, the value of the environment variable VV_OUTPUT_LOG_UTF8 is used instead. If the value of VV_OUTPUT_LOG_UTF8 is 1, it's UTF-8; if 0 or empty, or if the value doesn't exist, it's automatically determined by the environment.
  --cors_policy_mode {CorsPolicyMode.all,CorsPolicyMode.localapps}
                        CORS permission mode. Can specify either all or localapps. all allows everything. localapps limits the cross-origin resource sharing policy to app://. and localhost-related. Other origins can be added with the allow_origin option. Default is localapps. This option takes precedence over the settings file specified by --setting_file.
  --allow_origin [ALLOW_ORIGIN ...]
                        Specifies allowed origins. Multiple can be specified by separating with spaces. This option takes precedence over the settings file specified by --setting_file.
  --setting_file SETTING_FILE
                        Can specify a settings file.
  --preset_file PRESET_FILE
                        Can specify a preset file. If not specified, it searches for presets.yaml in the environment variable VV_PRESET_FILE and the user directory in that order.
  --disable_mutable_api
                        Disables APIs that modify static data of the engine, such as dictionary registration and setting changes. If not specified, the value of the environment variable VV_DISABLE_MUTABLE_API is used instead. If the value of VV_DISABLE_MUTABLE_API is 1, it's disabled; if 0 or empty, or if the value doesn't exist, it's ignored.
```

### Update

Delete all files in the engine directory and replace them with new ones.

## Contributor's Guide

VOICEVOX ENGINE welcomes your contributions!  
For details, please see [CONTRIBUTING.en.md](./CONTRIBUTING.en.md).  
We also have discussions and casual chats on the [VOICEVOX Unofficial Discord Server](https://discord.gg/WMwWetrzuh). Feel free to join us.

When creating a pull request to resolve an issue, we recommend either informing on the issue side that you've started working on it, or initially creating a Draft pull request to avoid working on the same issue as someone else.

## Developer's Guide

### Environment Setup

It is developed using `Python 3.11.9`.
To install, you'll need C/C++ compilers and CMake for each OS.

```bash
# Install runtime environment
python -m pip install -r requirements.txt

# Install development environment, test environment, and build environment
python -m pip install -r requirements-dev.txt -r requirements-build.txt
```

### Execution

For details on command-line arguments, check with the following command:

```bash
python run.py --help
```

```bash
# Start server with production version of VOICEVOX
VOICEVOX_DIR="C:/path/to/voicevox" # Path to production version VOICEVOX directory
python run.py --voicevox_dir=$VOICEVOX_DIR
```

<!-- Uncomment when replaceable voice libraries or their specifications are published
```bash
# Replace voice library
VOICELIB_DIR="C:/path/to/your/tts-model"
python run.py --voicevox_dir=$VOICEVOX_DIR --voicelib_dir=$VOICELIB_DIR
```
-->

```bash
# Start server with mock
python run.py --enable_mock
```

```bash
# Change log to UTF8
python run.py --output_log_utf8
# Or VV_OUTPUT_LOG_UTF8=1 python run.py
```

#### Specifying CPU Thread Count

If CPU thread count is not specified, half of the logical core count is used. (For most CPUs, this is half of the total processing power)  
If you're running on IaaS or a dedicated server, and want to adjust the processing power used by the engine, you can achieve this by specifying the CPU thread count.

- Specify with runtime argument
  ```bash
  python run.py --voicevox_dir=$VOICEVOX_DIR --cpu_num_threads=4
  ```
- Specify with environment variable
  ```bash
  export VV_CPU_NUM_THREADS=4
  python run.py --voicevox_dir=$VOICEVOX_DIR
  ```

#### Using Past Versions of the Core

It's possible to use VOICEVOX Core 0.5.4 or later.  
Support for libtorch version core on Mac is not available.

##### Specifying Past Binaries

By specifying the directory of the production version VOICEVOX or pre-compiled engine with the `--voicevox_dir` argument, that version of the core will be used.

```bash
python run.py --voicevox_dir="/path/to/voicevox"
```

On Mac, specifying `DYLD_LIBRARY_PATH` is necessary.

```bash
DYLD_LIBRARY_PATH="/path/to/voicevox" python run.py --voicevox_dir="/path/to/voicevox"
```

##### Directly Specifying Voice Library

Specify the directory of the unzipped [VOICEVOX Core zip file](https://github.com/VOICEVOX/voicevox_core/releases) with the `--voicelib_dir` argument.  
Also, specify the directory of [libtorch](https://pytorch.org/) or [onnxruntime](https://github.com/microsoft/onnxruntime) (shared library) with the `--runtime_dir` argument according to the core version.  
However, if libtorch and onnxruntime are in the system's search path, specifying the `--runtime_dir` argument is unnecessary.  
The `--voicelib_dir` and `--runtime_dir` arguments can be used multiple times.  
When specifying the core version in the API endpoint, use the `core_version` argument. (If not specified, the latest core will be used)

```bash
python run.py --voicelib_dir="/path/to/voicevox_core" --runtime_dir="/path/to/libtorch_or_onnx"
```

On Mac, specifying `DYLD_LIBRARY_PATH` is necessary instead of the `--runtime_dir` argument.

```bash
DYLD_LIBRARY_PATH="/path/to/onnx" python run.py --voicelib_dir="/path/to/voicevox_core"
```

##### Placing in User Directory

Voice libraries in the following directories are automatically loaded:

- Built version: `<user_data_dir>/voicevox-engine/core_libraries/`
- Python version: `<user_data_dir>/voicevox-engine-dev/core_libraries/`

`<user_data_dir>` varies depending on the OS.

- Windows: `C:\Users\<username>\AppData\Local\`
- macOS: `/Users/<username>/Library/Application\ Support/`
- Linux: `/home/<username>/.local/share/`

### Build

Local building is possible through packaging with `pyinstaller` and containerization with Dockerfile.  
For detailed procedures, please see [Contributor's Guide#Build](./CONTRIBUTING.en.md#build).

If using GitHub, you can build using GitHub Actions in your forked repository.  
Turn ON Actions and start `build-engine-package.yml` with workflow_dispatch to build.
The artifacts will be uploaded to Releases.
For GitHub Actions settings necessary for building, please see [Contributor's Guide#GitHub Actions](./CONTRIBUTING.md#github-actions).

### Testing and Static Analysis

Testing with `pytest` and static analysis with various linters are possible.  
For detailed procedures, please see [Contributor's Guide#Testing](./CONTRIBUTING.md#testing) and [Contributor's Guide#Static Analysis](./CONTRIBUTING.md#static-analysis).

### Dependencies

Dependencies are managed with `poetry`. Also, there are license restrictions on the dependent libraries that can be introduced.  
For details, please see [Contributor's Guide#Packages](./CONTRIBUTING.md#packages).

### About Multi-Engine Feature

In the VOICEVOX editor, you can start multiple engines simultaneously.
By using this feature, you can run your own voice synthesis engine or existing voice synthesis engines on the VOICEVOX editor.

<img src="./docs/res/マルチエンジン概念図.svg" width="320">

<details>

#### How the Multi-Engine Feature Works

The multi-engine feature is realized by starting multiple Web APIs of engines compliant with the VOICEVOX API on different ports and handling them uniformly.
The editor starts each engine via executable binary and individually manages settings and states by binding them to EngineID.

#### How to Support the Multi-Engine Feature

Support is possible by creating an executable binary that starts a VOICEVOX API compliant engine.
The easiest way is to fork the VOICEVOX ENGINE repository and modify some of its functions.

The points to modify are engine information, character information, and voice synthesis.

The engine information is managed in the manifest file (`engine_manifest.json`) in the root directory.
A manifest file in this format is required for VOICEVOX API compliant engines.
Please check the information in the manifest file and change it as appropriate.
Depending on the voice synthesis method, it may not be possible to have the same functions as VOICEVOX, such as morphing.
In that case, please change the information in `supported_features` in the manifest file as appropriate.

Character information is managed in files in the `resources/character_info` directory.
Dummy icons and such are prepared, so please change them as appropriate.

Voice synthesis is performed in `voicevox_engine/tts_pipeline/tts_engine.py`.
In the VOICEVOX API, voice synthesis is realized by the engine creating an initial value for the voice synthesis query `AudioQuery` and returning it to the user, the user editing the query as needed, and then the engine synthesizing voice according to the query.
Query creation is done at the `/audio_query` endpoint, and voice synthesis is done at the `/synthesis` endpoint. At minimum, supporting these two is sufficient to be compliant with the VOICEVOX API.

#### How to Distribute Multi-Engine Feature Compatible Engines

We recommend distributing as a VVPP file.
VVPP stands for "VOICEVOX Plugin Package," and it's essentially a Zip file of a directory containing the built engine and other files.
If you change the extension to `.vvpp`, it can be installed in the VOICEVOX editor with a double-click.

The editor side unzips the received VVPP file on the local disk, then explores files according to the `engine_manifest.json` in the root.
If you can't get it to load properly in the VOICEVOX editor, please refer to the editor's error log.

Also, `xxx.vvpp` can be distributed as `xxx.0.vvppp` files with sequential numbers.
This is useful when the file size is large and difficult to distribute.
The `vvpp` and `vvppp` files needed for installation are listed in the `vvpp.txt` file.

</details>

## Case Introductions

**[voicevox-client](https://github.com/voicevox-client) [@voicevox-client](https://github.com/voicevox-client)** ･･･ API wrappers for various languages for VOICEVOX ENGINE

## License

Dual license of LGPL v3 and another license that doesn't require source code disclosure.
If you want to obtain the other license, please ask Hiho.  
X account: [@hiho_karuta](https://x.com/hiho_karuta)
