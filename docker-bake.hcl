target "default" {
  context = "."
  tags = [ "voicevox/voicevox_engine:latest" ]
  args = {
    VOICEVOX_ENGINE_REPOSITORY = "voicevox/voicevox_engine"
    VOICEVOX_ENGINE_VERSION = "0.25.0"
    VOICEVOX_ENGINE_TARGET = "linux-cpu-x64"
  }
}

target "cpu" {
  inherits = [ "default" ]
  target = "runtime-env"
}

target "nvidia" {
  inherits = [ "default" ]
  args = {
    VOICEVOX_ENGINE_TARGET = "linux-nvidia"
  }
  target = "runtime-nvidia-env"
}
