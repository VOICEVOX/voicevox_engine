import os
import re
import tarfile
from os.path import exists
from pathlib import PurePath
from typing import Optional
from typing.io import IO
from urllib.request import urlretrieve

import numpy as np
import pkg_resources
import pyworld as pw
from scipy.io import wavfile
from scipy.signal import resample

from .julius4seg import converter, sp_inserter
from .julius4seg.sp_inserter import ModelType, space_symbols
from .kana_parser import parse_kana

JULIUS_SAMPLE_RATE = 16000
FRAME_PERIOD = 1.0
PUNCTUATION = ["_", "'", "/", "、"]
SIL_SYMBOL = ["silB", "silE", "sp"]
TMP_PATH = "tmp.wav"
UUT_ID = "tmp"
TEMP_FILE_LIST = [
    "first_pass.dfa",
    "first_pass.dict",
    "second_pass.dfa",
    "second_pass.dict",
    "tmp.wav",
]

_JULIUS_DICTATION_URL = "https://github.com/julius-speech/dictation-kit/archive/refs/tags/dictation-kit-v4.3.1.tar.gz"  # noqa: B950
JULIUS_DICTATION_DIR = os.environ.get(
    "JULIUS_DICTATION_DIR",
    # they did put two "dictation-kit"s in extracted folder name
    pkg_resources.resource_filename(__name__, "dictation-kit-dictation-kit-v4.3.1"),
)

sp_inserter.JULIUS_ROOT = PurePath(JULIUS_DICTATION_DIR)


class PhraseInfo:
    def __init__(self, pitch: float, length: float, phoneme: str):
        self.pitch = pitch
        self.length = length
        self.phoneme = phoneme


def _lazy_init():
    if not exists(JULIUS_DICTATION_DIR):
        print("Julius not found, Downloading")
        _extract_julius()


def _extract_julius():
    global JULIUS_DICTATION_DIR
    filename = pkg_resources.resource_filename(__name__, "dictation-kit.tar.gz")
    print("Downloading Julius...", _JULIUS_DICTATION_URL)
    urlretrieve(_JULIUS_DICTATION_URL, filename)
    print("Extracting Julius...", JULIUS_DICTATION_DIR)
    with tarfile.open(filename, mode="r|gz") as f:
        f.extractall(path=pkg_resources.resource_filename(__name__, ""))
    JULIUS_DICTATION_DIR = pkg_resources.resource_filename(
        __name__, "dictation-kit-dictation-kit-v4.3.1"
    )
    sp_inserter.JULIUS_ROOT = PurePath(JULIUS_DICTATION_DIR)
    os.remove(filename)


def resample_ts(timestamp: str):
    return int((float(timestamp) * 0.9375))


# can't define type for engine because it causes a circular import
def _predict_avg_pitch(engine, kana: str, speaker_id: int):
    predicted_phrases, _ = parse_kana(kana, False)
    engine.replace_mora_data(predicted_phrases, speaker_id=speaker_id)
    pitch_list = []
    for phrase in predicted_phrases:
        for mora in phrase.moras:
            pitch_list.append(mora.pitch)
    pitch_list = np.array(pitch_list, dtype=np.float64)
    return _no_nan(np.average(pitch_list[pitch_list != 0]))


def get_normalize_scale(engine, kana: str, f0: np.ndarray, speaker_id: int):
    f0_avg = _no_nan(np.average(f0[f0 != 0]))
    predicted_avg = _predict_avg_pitch(engine, kana, speaker_id)
    return predicted_avg / f0_avg


def _no_nan(num):
    return 0.0 if np.isnan(num) else num


def extract_guided_feature(audio_file: Optional[IO], kana: str):
    _lazy_init()
    sr, wave = wavfile.read(audio_file)
    # stereo to mono
    if len(wave.shape) == 2:
        wave = wave.sum(axis=1) / 2

    f0 = extract_f0(wave, sr, 256 / 24000 * 1000)

    julius_wave = resample(wave, JULIUS_SAMPLE_RATE * len(wave) // sr)

    # normalization for different WAV format
    if julius_wave.dtype == "float32":
        julius_wave *= 32767
    if julius_wave.dtype == "int32":
        julius_wave = np.floor_divide(julius_wave, 2147483392 / 32767)
    if julius_wave.dtype == "uint8":
        # floor of 32767 / 255
        julius_wave *= 128

    julius_wave = julius_wave.astype(np.int16)

    julius_kana = re.sub(
        "|".join(PUNCTUATION), "", kana.replace("/", "").replace("、", " ")
    )

    phones = forced_align(julius_wave, julius_kana)
    return f0, phones


def forced_align(julius_wave: np.ndarray, base_kata_text: str):
    model_type = ModelType.gmm
    hmm_model = os.path.join(
        JULIUS_DICTATION_DIR, "model/phone_m/jnas-mono-16mix-gid.binhmm"
    )
    options = []

    base_kata_text = sp_inserter.kata2hira(base_kata_text)

    julius_phones = [converter.conv2openjtalk(hira) for hira in base_kata_text.split()]

    base_kan_text = ["sym_{}".format(i) for i in range(len(julius_phones))]

    assert len(base_kan_text) == len(julius_phones), f"{base_kan_text}\n{julius_phones}"

    dict_1st = sp_inserter.gen_julius_dict_1st(base_kan_text, julius_phones, model_type)
    dfa_1st = sp_inserter.gen_julius_dfa(dict_1st.count("\n"))

    with open("first_pass.dict", "w", encoding="utf-8") as f:
        f.write(dict_1st)

    with open("first_pass.dfa", "w", encoding="utf-8") as f:
        f.write(dfa_1st)
    wavfile.write(TMP_PATH, JULIUS_SAMPLE_RATE, julius_wave)

    raw_first_output = sp_inserter.julius_sp_insert(
        TMP_PATH,
        "first_pass",
        hmm_model,
        model_type,
        options,
    )

    forced_phones_with_sp = []
    try:
        _, sp_position = sp_inserter.get_sp_inserted_text(raw_first_output)

        for j, (_t, p) in enumerate(zip(base_kan_text, julius_phones)):
            forced_phones_with_sp.append(p)
            if j in sp_position:
                forced_phones_with_sp.append(space_symbols[model_type])

        forced_phones_with_sp = " ".join(forced_phones_with_sp)
    except Exception:
        pass

    phones_with_sp = sp_inserter.get_sp_inserterd_phone_seqence(
        raw_first_output, model_type
    )
    if len(phones_with_sp) < 2:
        forced_phones_with_sp = phones_with_sp

    dict_2nd = sp_inserter.gen_julius_dict_2nd(forced_phones_with_sp, model_type)
    dfa_2nd = sp_inserter.gen_julius_aliment_dfa(dict_2nd.count("\n"))

    with open("second_pass.dict", "w") as f:
        f.write(dict_2nd)

    with open("second_pass.dfa", "w") as f:
        f.write(dfa_2nd)

    raw_second_output = sp_inserter.julius_phone_alignment(
        TMP_PATH, "second_pass", hmm_model, model_type, options
    )
    time_alimented_list = sp_inserter.get_time_alimented_list(raw_second_output)

    assert len(time_alimented_list) > 0, raw_second_output

    for file in TEMP_FILE_LIST:
        os.remove(file)

    return time_alimented_list


def extract_f0(wave: np.ndarray, sr: int, frame_period: float):
    w = wave.astype(np.float64)
    f0, t = pw.harvest(w, sr, frame_period=frame_period)
    vuv = f0 != 0
    f0_log = np.zeros_like(f0)
    f0_log[vuv] = np.log(f0[vuv])
    return f0_log
