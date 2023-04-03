
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

## Connect to database
Define connection url in database/setting.py
```
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
```
Run with mock engine
```
python run.py --enable_mock
```
Sign up and Login to get Authorization token
![image](https://user-images.githubusercontent.com/128009347/229417156-60b2008e-c555-42c2-8d5e-4f58967eebd8.png)

Then, copy access_token and parse it to Headers when call 2 endpoints voice_voice and text_voice
![image](https://user-images.githubusercontent.com/128009347/229417374-72310ec3-cc11-4855-8a0b-2c9bdfb2bde2.png)
