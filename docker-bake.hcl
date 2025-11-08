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
  tags = [ "voicevox/voicevox_engine:latest-cpu" ]
  target = "runtime-env"
}

target "nvidia" {
  inherits = [ "default" ]
  tags = [ "voicevox/voicevox_engine:latest-nvidia" ]
  args = {
    VOICEVOX_ENGINE_TARGET = "linux-nvidia"
  }
  target = "runtime-nvidia-env"
}
