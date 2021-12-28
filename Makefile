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
		-t hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest \
		--target runtime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:focal \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core_cpu $(ARGS)

.PHONY: run-linux-docker-ubuntu20.04
run-linux-docker-ubuntu20.04:
	docker run --rm -it \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		hiroshiba/voicevox_engine:cpu-ubuntu20.04-latest $(CMD)

.PHONY: build-linux-docker-nvidia-ubuntu20.04
build-linux-docker-nvidia-ubuntu20.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest \
		--target runtime-nvidia-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/driver:460.73.01-ubuntu20.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core $(ARGS)

.PHONY: run-linux-docker-nvidia-ubuntu20.04
run-linux-docker-nvidia-ubuntu20.04:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		hiroshiba/voicevox_engine:nvidia-ubuntu20.04-latest $(CMD)


# Ubuntu 18.04
.PHONY: build-linux-docker-ubuntu18.04
build-linux-docker-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:cpu-ubuntu18.04-latest \
		--target runtime-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:bionic \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_cpu_x64.so \
		--build-arg USE_GLIBC_231_WORKAROUND=1 $(ARGS)

.PHONY: run-linux-docker-ubuntu18.04
run-linux-docker-ubuntu18.04:
	docker run --rm -it \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		hiroshiba/voicevox_engine:cpu-ubuntu18.04-latest $(CMD)

.PHONY: build-linux-docker-nvidia-ubuntu18.04
build-linux-docker-nvidia-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:nvidia-ubuntu18.04-latest \
		--target runtime-nvidia-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/driver:460.73.01-ubuntu18.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=libcore_gpu_x64_nvidia.so \
		--build-arg USE_GLIBC_231_WORKAROUND=1 $(ARGS)

.PHONY: run-linux-docker-nvidia-ubuntu18.04
run-linux-docker-nvidia-ubuntu18.04:
	docker run --rm -it \
		--gpus all \
		-p '127.0.0.1:50021:50021' $(ARGS) \
		hiroshiba/voicevox_engine:nvidia-ubuntu18.04-latest $(CMD)


# VOICEVOX Core env for test
.PHONY: build-linux-docker-download-core-env-ubuntu18.04
build-linux-docker-download-core-env-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:download-core-env-ubuntu18.04 \
		--target download-core-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic $(ARGS)

.PHONY: run-linux-docker-download-core-env-ubuntu18.04
run-linux-docker-download-core-env-ubuntu18.04:
	docker run --rm -it $(ARGS) \
		hiroshiba/voicevox_engine:download-core-env-ubuntu18.04 $(CMD)

# LibTorch env for test
.PHONY: build-linux-docker-download-libtorch-env-ubuntu18.04
build-linux-docker-download-libtorch-env-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:download-libtorch-env-ubuntu18.04 \
		--target download-libtorch-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic $(ARGS)

.PHONY: run-linux-docker-download-libtorch-env-ubuntu18.04
run-linux-docker-download-libtorch-env-ubuntu18.04:
	docker run --rm -it $(ARGS) \
		hiroshiba/voicevox_engine:download-libtorch-env-ubuntu18.04 $(CMD)


# Python env for test
.PHONY: build-linux-docker-compile-python-env
build-linux-docker-compile-python-env:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:compile-python-env \
		--target compile-python-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal $(ARGS)

.PHONY: run-linux-docker-compile-python-env
run-linux-docker-compile-python-env:
	docker run --rm -it $(ARGS) \
		hiroshiba/voicevox_engine:compile-python-env $(CMD)


# Build linux binary in Docker
## Ubuntu 20.04
.PHONY: build-linux-docker-build-ubuntu20.04
build-linux-docker-build-ubuntu20.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-cpu-ubuntu20.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:focal \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core_cpu $(ARGS)

.PHONY: run-linux-docker-build-ubuntu20.04
run-linux-docker-build-ubuntu20.04:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" $(ARGS) \
		hiroshiba/voicevox_engine:build-cpu-ubuntu20.04-latest $(CMD)

.PHONY: build-linux-docker-build-nvidia-ubuntu20.04
build-linux-docker-build-nvidia-ubuntu20.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-nvidia-ubuntu20.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:focal \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/driver:460.73.01-ubuntu20.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core $(ARGS)

.PHONY: run-linux-docker-build-nvidia-ubuntu20.04
run-linux-docker-build-nvidia-ubuntu20.04:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" $(ARGS) \
		hiroshiba/voicevox_engine:build-nvidia-ubuntu20.04-latest $(CMD)

## Ubuntu 18.04
.PHONY: build-linux-docker-build-ubuntu18.04
build-linux-docker-build-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-cpu-ubuntu18.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic \
		--build-arg BASE_RUNTIME_IMAGE=ubuntu:bionic \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core_cpu \
		--build-arg USE_GLIBC_231_WORKAROUND=1 $(ARGS)

.PHONY: run-linux-docker-build-ubuntu18.04
run-linux-docker-build-ubuntu18.04:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" $(ARGS) \
		hiroshiba/voicevox_engine:build-cpu-ubuntu18.04-latest $(CMD)

.PHONY: build-linux-docker-build-nvidia-ubuntu18.04
build-linux-docker-build-nvidia-ubuntu18.04:
	docker buildx build . \
		-t hiroshiba/voicevox_engine:build-nvidia-ubuntu18.04-latest \
		--target build-env \
		--progress plain \
		--build-arg BASE_IMAGE=ubuntu:bionic \
		--build-arg BASE_RUNTIME_IMAGE=nvidia/driver:460.73.01-ubuntu18.04 \
		--build-arg LIBTORCH_URL=https://download.pytorch.org/libtorch/cu111/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcu111.zip \
		--build-arg VOICEVOX_CORE_LIBRARY_NAME=core \
		--build-arg USE_GLIBC_231_WORKAROUND=1 $(ARGS)

.PHONY: run-linux-docker-build-nvidia-ubuntu18.04
run-linux-docker-build-nvidia-ubuntu18.04:
	docker run --rm -it \
		-v "$(shell pwd)/cache/Nuitka:/home/user/.cache/Nuitka" \
		-v "$(shell pwd)/build:/opt/voicevox_engine_build" $(ARGS) \
		hiroshiba/voicevox_engine:build-nvidia-ubuntu18.04-latest $(CMD)
