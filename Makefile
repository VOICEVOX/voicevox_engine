CMD=

build-linux-docker:
	docker buildx build . -t voicevox/voicevox_engine

run-linux-docker:
	docker run --rm -it -p '127.0.0.1:50021:50021' voicevox/voicevox_engine $(CMD)
