CMD=

.PHONY: build-linux-docker-ubuntu
build-linux-docker-ubuntu:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest \
		--target runtime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:focal \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_SO_NAME=libcore_cpu.so

.PHONY: run-linux-docker-ubuntu
run-linux-docker-ubuntu:
	docker run --rm -it \
		-p '127.0.0.1:50021:50021' \
		hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest $(CMD)

.PHONY: build-linux-docker-nvidia
build-linux-docker-nvidia:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest \
		--target runtime-nvidia-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/cuda:11.4.1-cudnn8-runtime-ubuntu20.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_SO_NAME=libcore.so

.PHONY: run-linux-docker-nvidia
run-linux-docker-nvidia:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' \
		hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest $(CMD)

.PHONY: build-linux-docker-compile-python-env
build-linux-docker-compile-python-env:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:compile-python-env \
		--target compile-python-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal

.PHONY: run-linux-docker-compile-python-env
run-linux-docker-compile-python-env:
	docker run --rm -it \
		hiroshiba/voicevox_engine:compile-python-env $(CMD)

# Build linux binary in Docker
.PHONY: build-linux-docker-build
build-linux-docker-build:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-cpu-ubuntu20.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:focal \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_SO_NAME=libcore_cpu.so

.PHONY: run-linux-docker-build
run-linux-docker-build:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" \
		hiroshiba/voicevox_engine:build-cpu-ubuntu20.04-latest $(CMD)


.PHONY: build-linux-docker-build-nvidia
build-linux-docker-build-nvidia:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-nvidia-ubuntu20.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/cuda:11.4.1-cudnn8-runtime-ubuntu20.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_SO_NAME=libcore.so

.PHONY: run-linux-docker-build-nvidia
run-linux-docker-build-nvidia:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" \
		hiroshiba/voicevox_engine:build-nvidia-ubuntu20.04-latest $(CMD)
