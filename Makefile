CMD=
NOCACHE=

ARGS:=
ifeq ($(NOCACHE),1)
	ARGS:=$(ARGS) --no-cache
endif

# Ubuntu 20.04
.PHONY: build-linux-docker-ubuntu20.04
build-linux-docker-ubuntu20.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:cpu-ubuntu20.04-latest \
		--target runtime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:20.04 \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:20.04 \
		--build-arg ONNXRUNTIME_URL=https://github.com/microsoft/onnxruntime/releases/download/v1.13.1/onnxruntime-linux-x64-1.13.1.tgz \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_cpu_x64.so $(ARGS)

.PHONY: run-linux-docker-ubuntu20.04
run-linux-docker-ubuntu20.04:
	docker run --rm -it \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		voicevox/voicevox_engine:cpu-ubuntu20.04-latest $(CMD)

.PHONY: build-linux-docker-nvidia-ubuntu20.04
build-linux-docker-nvidia-ubuntu20.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:nvidia-ubuntu20.04-latest \
		--target runtime-nvidia-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:20.04 \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04 \
		--build-arg ONNXRUNTIME_URL=https://github.com/microsoft/onnxruntime/releases/download/v1.13.1/onnxruntime-linux-x64-gpu-1.13.1.tgz \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_gpu_x64_nvidia.so $(ARGS)

.PHONY: run-linux-docker-nvidia-ubuntu20.04
run-linux-docker-nvidia-ubuntu20.04:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		voicevox/voicevox_engine:nvidia-ubuntu20.04-latest $(CMD)


# Ubuntu 18.04
.PHONY: build-linux-docker-ubuntu18.04
build-linux-docker-ubuntu18.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:cpu-ubuntu18.04-latest \
		--target runtime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:18.04 \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:18.04 \
		--build-arg ONNXRUNTIME_URL=https://github.com/microsoft/onnxruntime/releases/download/v1.13.1/onnxruntime-linux-x64-1.13.1.tgz \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_cpu_x64.so $(ARGS)

.PHONY: run-linux-docker-ubuntu18.04
run-linux-docker-ubuntu18.04:
	docker run --rm -it \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		voicevox/voicevox_engine:cpu-ubuntu18.04-latest $(CMD)

.PHONY: build-linux-docker-nvidia-ubuntu18.04
build-linux-docker-nvidia-ubuntu18.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:nvidia-ubuntu18.04-latest \
		--target runtime-nvidia-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:18.04 \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu18.04 \
		--build-arg ONNXRUNTIME_URL=https://github.com/microsoft/onnxruntime/releases/download/v1.13.1/onnxruntime-linux-x64-gpu-1.13.1.tgz \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_gpu_x64_nvidia.so $(ARGS)

.PHONY: run-linux-docker-nvidia-ubuntu18.04
run-linux-docker-nvidia-ubuntu18.04:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		voicevox/voicevox_engine:nvidia-ubuntu18.04-latest $(CMD)


# VOICEVOX Core env for test
.PHONY: build-linux-docker-download-core-env-ubuntu18.04
build-linux-docker-download-core-env-ubuntu18.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:download-core-env-ubuntu18.04 \
		--target download-core-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:18.04 $(ARGS)

.PHONY: run-linux-docker-download-core-env-ubuntu18.04
run-linux-docker-download-core-env-ubuntu18.04:
	docker run --rm -it $(ARGS) \
		voicevox/voicevox_engine:download-core-env-ubuntu18.04 $(CMD)


# ONNX Runtime env for test
.PHONY: build-linux-docker-download-onnxruntime-env-ubuntu18.04
build-linux-docker-download-onnxruntime-env-ubuntu18.04:
	docker buildx build . \
		-t voicevox/voicevox_engine:download-onnxruntime-env-ubuntu18.04 \
		--target download-onnxruntime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:18.04 $(ARGS)

.PHONY: run-linux-docker-download-onnxruntime-env-ubuntu18.04
run-linux-docker-download-onnxruntime-env-ubuntu18.04:
	docker run --rm -it $(ARGS) \
		voicevox/voicevox_engine:download-onnxruntime-env-ubuntu18.04 $(CMD)


# Python env for test
.PHONY: build-linux-docker-compile-python-env
build-linux-docker-compile-python-env:
	docker buildx build . \
		-t voicevox/voicevox_engine:compile-python-env \
		--target compile-python-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:20.04 $(ARGS)

.PHONY: run-linux-docker-compile-python-env
run-linux-docker-compile-python-env:
	docker run --rm -it $(ARGS) \
		voicevox/voicevox_engine:compile-python-env $(CMD)
