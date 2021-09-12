CMD=

build-linux-docker-nvidia:
	docker buildx build . \
		-t aoirint/voicevox_engine:nvidia-ubuntu20.04 \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/cuda:11.4.1-cudnn8-runtime-ubuntu20.04

run-linux-docker-nvidia:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' \
		aoirint/voicevox_engine:nvidia-ubuntu20.04 $(CMD)
