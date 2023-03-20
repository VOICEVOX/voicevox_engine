
# Requirement

1. python 3.8, pip
2. ffmpeg
3. download and extract voicevox_engine https://github.com/VOICEVOX/voicevox_engine/releases
4. set environment variable OPENAI_KEY


Environment and dependencies

```
python3 -m venv venv
./venv/bin/activate
pip install -r requirements.txt
```

Api doc generate

```
python make_docs.py
```

Run local server

```
python run.py --voicevox_dir=voicevox_engine_folder
```

Api docs

http://localhost:50021/docs

We have 2 endpoints

http://localhost:50021/voice_voice?speaker=1&whisper=true
http://localhost:50021/text_voice?speaker=1&text=すぐ修正できそうですか？

whisper=true => use whisper API
whisper=false => use local speech to text model (slower)

API accepts .wav file

# Docker

```
docker build .
docker run -p 50021:50021 -e OPENAI_KEY=xxx container_id
```
