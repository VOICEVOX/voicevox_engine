import tarfile
from pathlib import PurePath
from typing import List

import re
import os
import pkg_resources
import numpy as np
import pyworld as pw
from scipy.signal import resample
from scipy.io import wavfile
from os.path import exists
from urllib.request import urlretrieve
from .julius4seg import sp_inserter

from .synthesis_engine import SynthesisEngine


JULIUS_SAMPLE_RATE = 16000
VOICEVOX_SAMPLE_RATE = 24000
FRAME_PERIOD = 1.0
PUNCTUATION = ["_", "'", "/", "、"]
TMP_PATH = "tmp.wav"
UUT_ID = "tmp"
TEMP_FILE_LIST = ["first_pass.dfa", "first_pass.dict", "second_pass.dfa", "second_pass.dict", "tmp.wav"]

_JULIUS_DICTATION_URL = "https://github.com/julius-speech/dictation-kit/archive/refs/tags/dictation-kit-v4.3.1.tar.gz"
JULIUS_DICTATION_DIR = os.environ.get(
    "JULIUS_DICTATION_DIR",
    # I don't know the reason but they did put two "dictation-kit"s in extracted folder name
    pkg_resources.resource_filename(__name__, "dictation-kit-dictation-kit-v4.3.1"),
).encode("ascii")


# benchmark decorator
def timereps(reps, func):
    from time import time
    start = time()
    for i in range(0, reps):
        func()
    end = time()
    return (end - start) / reps


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
    JULIUS_DICTATION_DIR = pkg_resources.resource_filename(__name__, "dictation-kit-dictation-kit-v4.3.1").encode("ascii")
    os.remove(filename)


# Get f0 query with pw, segment with julius and send to forward decoder
def synthesis(audio_file, kana: str) -> np.ndarray:
    _lazy_init()
    sp_inserter.JULIUS_ROOT = PurePath(JULIUS_DICTATION_DIR.decode("ascii"))
    sr, wave = wavfile.read(audio_file)
    julius_wave = resample(wave.astype(np.int16), JULIUS_SAMPLE_RATE * len(wave) // sr)
    julius_kana = re.sub("|".join(PUNCTUATION), "", kana.replace("/", " "))

    forced_align(julius_wave, julius_kana)

    return extract_pitch(wave, sr)


def forced_align(julius_wave: np.ndarray, base_kata_text: str):
    base_kan_text = ['sym_{}'.format(i) for i in range(len(base_kata_text.split()))]
    julius_phonemes = [sp_inserter.conv2julius(hira) for hira in [sp_inserter.kata2hira(kata) for kata in base_kata_text.split(" ")]]
    dict_1st = sp_inserter.gen_julius_dict_1st(base_kan_text, julius_phonemes)
    dfa_1st = sp_inserter.gen_julius_dfa(dict_1st.count('\n'))

    with open('first_pass.dict', 'w', encoding="utf-8") as f:
        f.write(dict_1st)

    with open('first_pass.dfa', 'w', encoding="utf-8") as f:
        f.write(dfa_1st)

    wavfile.write(TMP_PATH, JULIUS_SAMPLE_RATE, julius_wave.astype(np.int16))

    raw_first_output = sp_inserter.julius_sp_insert(TMP_PATH, 'first_pass', None)

    forced_phones_with_sp = []

    _, sp_position = sp_inserter.get_sp_inserted_text(raw_first_output, UUT_ID)

    for j, zipped in enumerate(zip(base_kan_text, julius_phonemes)):
        forced_phones_with_sp.append(zipped[1])
        if j in sp_position:
            forced_phones_with_sp.append('sp')

    forced_phones_with_sp = ' '.join(forced_phones_with_sp)

    phones_with_sp = sp_inserter.get_sp_inserterd_phone_seqence(raw_first_output, UUT_ID)
    if len(forced_phones_with_sp) < 2:
        forced_phones_with_sp = phones_with_sp

    dict_2nd = sp_inserter.gen_julius_dict_2nd(forced_phones_with_sp)
    dfa_2nd = sp_inserter.gen_julius_aliment_dfa()

    with open('second_pass.dict', 'w') as f:
        f.write(dict_2nd)

    with open('second_pass.dfa', 'w') as f:
        f.write(dfa_2nd)

    raw_second_output = sp_inserter.julius_phone_alignment(TMP_PATH, 'second_pass')

    time_alimented_list = sp_inserter.get_time_alimented_list(raw_second_output)

    for file in TEMP_FILE_LIST:
        os.remove(file)

    return time_alimented_list


def extract_pitch(wave: np.ndarray, sr: int) -> np.ndarray:
    frame_period = 1.0
    world_wave = wave.astype(np.double)
    f0, time_axis = pw.harvest(world_wave, sr, frame_period=frame_period)

    return f0
