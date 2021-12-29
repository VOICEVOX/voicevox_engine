import re
import subprocess
import sys
from enum import Enum
from itertools import chain
from typing import List, Optional, Tuple


class ModelType(str, Enum):
    gmm = "gmm"
    dnn = "dnn"


JULIUS_ROOT = "."

begin_silent_symbols = {ModelType.gmm: "silB", ModelType.dnn: "sp_B"}
end_silent_symbols = {ModelType.gmm: "silE", ModelType.dnn: "sp_E"}
space_symbols = {ModelType.gmm: "sp", ModelType.dnn: "sp_S"}


def get_os_dependent_directory() -> str:
    """Juluis Segmentaion-Kitのディレクトリ名をOSの種類から取得
    returns:
        (str): OS依存のパスの一部
    """
    if sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        return "windows"
    elif sys.platform.startswith("darwin"):
        return "osx"
    elif sys.platform.startswith("linux"):
        return "linux"


def get_os_dependent_exec() -> str:
    """Juliusの実行ファイル名を取得
    returns:
        (str): Juliusの実行ファイル名
    """
    if sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        return "julius.exe"
    else:
        return "julius"


def get_os_dependent_echo(filename: str) -> list:
    """ Get parameters of echo referencing platforms
    Returns:
        list[str]: echo parameters
    """
    if sys.platform.startswith("win") or sys.platform.startswith('cygwin'):
        return ["cmd.exe", "/c", "echo " + filename]
    else:
        return ["echo", filename]


def kata2hira(kana: str) -> str:
    """ヵ，ヶ以外のカタカナをひらがなに変換
    args:
        kana(str): カタカナ文字列
            "ヤキニク"
    returns:
        (str): ひらがな文字列
            "やきにく"
    """
    return "".join(
        [
            chr(ord(c) + ord("あ") - ord("ア")) if ord("ァ") <= ord(c) <= ord("ヴ") else c
            for c in kana
        ]
    )


def gen_julius_dict_1st(
    text_symbols: List[str], word_phones: List[str], model_type: ModelType
) -> str:
    """テキストのシンボルと読みの音素のJulius dictファイルの中身を生成
    args:
        text_symbols ([str]): 単語のシンボル
            ['今回', 'は']
        word_phones ([str]): 単語の音素系列
            ['k o N k a i', 'w a']
    returns:
        (str): Juliusのdictファイルの中身
    """
    tmp = []
    finit = len(text_symbols)

    for i, zipped in enumerate(zip(text_symbols, word_phones)):
        tmp.append("{}\t[{}]\t{}".format(i * 2, *zipped))
        if i + 1 != finit:
            tmp.append(
                "{}\t[{}]\t{}".format(
                    i * 2 + 1, "sp_{}".format(i), space_symbols[model_type]
                )
            )

    # append sp and Start, End symbol
    tmp.append(
        "{}\t[{}]\t{}".format(i * 2 + 1, "<s>", begin_silent_symbols[model_type])
    )
    tmp.append(
        "{}\t[{}]\t{}".format((i + 1) * 2, "</s>", end_silent_symbols[model_type])
    )

    return "\n".join(tmp) + "\n"


def gen_julius_dfa(number_of_words: int) -> str:
    """単語数から遷移のためのJuliusのdfaファイルの中身を生成
    args:
        number_of_words (int): 遷移する単語の単語数
    returns:
        (str): Juliusのdfaファイルの中身
    """
    i = 0
    current_word = number_of_words - 3
    isLast = False
    tmp = []
    while True:
        if i == 0:
            tmp.append("{} {} {} {} {}".format(i, number_of_words - 1, i + 1, 0, 1))
            i += 1
        elif i > 0 and not isLast:
            tmp.append("{} {} {} {} {}".format(i, current_word, i + 1, 0, 0))
            current_word -= 1
            isLast = current_word == -1
            i += 1
        elif i > 0 and isLast:
            tmp.append("{} {} {} {} {}".format(i, i - 1, i + 1, 0, 0))
            tmp.append("{} {} {} {} {}".format(i + 1, -1, -1, 1, 0))
            break

    return "\n".join(tmp) + "\n"


def gen_julius_dict_2nd(phone_seqence: str, model_type: ModelType) -> str:
    """音素系列から強制アライメントのためのdictファイルの中身を生成
    args:
        phone_seqence (str):
            'k o N k a i w a '
    returns:
        (str): Juliusのdictファイルの中身
    """
    phone_seqences = phone_seqence.split(f" {space_symbols[model_type]} ")
    return (
        "\n".join(
            [
                f"{i}\t[w_{i}]\t"
                + phone_seqence
                + (
                    f" {space_symbols[model_type]}"
                    if i != len(phone_seqences) - 1
                    else ""
                )
                for i, phone_seqence in enumerate(phone_seqences)
            ]
            + [
                f"{len(phone_seqences)}\t[w_{len(phone_seqences)}]\t"
                + begin_silent_symbols[model_type]
            ]
            + [
                f"{len(phone_seqences) + 1}\t[w_{len(phone_seqences) + 1}]\t"
                + end_silent_symbols[model_type]
            ]
        )
        + "\n"
    )


def gen_julius_aliment_dfa(number_of_words: int) -> str:
    """強制アライメント用のdfaファイルの中身を生成
    returns:
        (str): Juliusのdfaファイルの中身
    """
    return gen_julius_dfa(number_of_words)


def julius_sp_insert(
    target_wav_file: str,
    aliment_file_signiture: str,
    model_path: str,
    model_type: ModelType,
    options: Optional[List[str]],
) -> List[str]:
    if options is None:
        options = []

    julius_args = {
        "-h": model_path,
        "-input": "file",
        "-debug": "",
        "-gram": aliment_file_signiture,
        "-nostrip": "",
        "-spmodel": space_symbols[model_type],
    }

    file_echo_p = subprocess.Popen(
        get_os_dependent_echo(target_wav_file), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    julius_p = subprocess.Popen(
        " ".join(
            [
                str(JULIUS_ROOT / 'bin' / get_os_dependent_directory() / get_os_dependent_exec()),
                *list(chain.from_iterable([[k, v] for k, v in julius_args.items()])),
            ]
            + options
        ).split(),
        stdin=file_echo_p.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    file_echo_p.stdout.close()
    return julius_p.communicate()[0].decode("utf-8").split("\n")


def get_sp_inserted_text(raw_output: List[str]) -> Tuple[str, List[int]] or None:
    """デコード結果からsp挿入後のテキストとspのインデックスを取得する
    args:
        raw_output: `julius_sp_insert`の出力
    returns:
        Tuple(str, [int]): デコード結果とspのindex
    """
    r = re.compile("<s> (.*) </s>")
    pass1_best = next(s for s in raw_output if s.startswith("pass1_best"))
    matched = r.search(pass1_best)
    if matched is None:
        raise Exception("Decode Failed")

    return (
        re.sub(r"sp_[\d+]", "<sp>", matched.group(1)),
        [int(s.split("_")[1]) for s in matched.group().split() if "sp_" in s],
    )


def get_sp_inserterd_phone_seqence(raw_output: List[str], model_type: ModelType) -> str:
    try:
        pass1_best_phonemeseq = next(
            s.rstrip("\r") for s in raw_output if s.startswith("pass1_best_phonemeseq")
        )
    except Exception as e:
        raise (e)

    complete_re = re.compile(
        begin_silent_symbols[model_type]
        + r" \| (.*) \| "
        + end_silent_symbols[model_type]
    )
    failed_re_1 = re.compile(
        end_silent_symbols[model_type]
        + r" \| (.*) \| "
        + begin_silent_symbols[model_type]
    )
    failed_re_2 = re.compile(end_silent_symbols[model_type] + r" \| (.*)")

    if complete_re.search(pass1_best_phonemeseq) is not None:
        matched = complete_re.search(pass1_best_phonemeseq)
    elif failed_re_1.search(pass1_best_phonemeseq) is not None:
        matched = failed_re_1.search(pass1_best_phonemeseq)
    elif failed_re_2.search(pass1_best_phonemeseq) is not None:
        matched = failed_re_2.search(pass1_best_phonemeseq)
    else:
        raise Exception("Decode Failed")

    tmp = matched.group(1)
    return " ".join([s.strip() for s in tmp.split("|")])


def julius_phone_alignment(
    target_wav_file: str,
    aliment_file_signiture: str,
    model_path: str,
    model_type: ModelType,
    options: Optional[List[str]],
) -> List[str]:
    if options is None:
        options = []

    julius_args = {
        "-h": model_path,
        "-palign": "",
        "-input": "file",
        "-gram": aliment_file_signiture,
        "-nostrip": "",
        "-n": "10",
        "-s": "10000",
        "-sb": "5000",
        "-spmodel": space_symbols[model_type],
    }

    file_echo_p = subprocess.Popen(
        ["echo", target_wav_file], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    julius_p = subprocess.Popen(
        " ".join(
            [
                str(JULIUS_ROOT / 'bin' / get_os_dependent_directory() / get_os_dependent_exec()),
                *list(chain.from_iterable([[k, v] for k, v in julius_args.items()])),
            ]
            + options
        ).split(),
        stdin=file_echo_p.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    file_echo_p.stdout.close()
    return julius_p.communicate()[0].decode("utf-8").split("\n")


def get_time_alimented_list(raw_output: List[str]) -> List[Tuple[str, str, str]]:
    r = re.compile(
        r"\[\s*(\d+)\s+(\d+)\s*\]"
        r"\s*[\-]*[\d,\.]+\s*"
        r"\{?([\w,\:]+)\-?([\w,\:]*)\+?([\w,\:]*)\}?\[?[\w,\:,\-,\+]*\]?$"
    )

    def get_phoneme(left: str, center: str, right: str):
        if len(center) == 0 and len(right) == 0:  # monophone
            return left
        elif len(center) > 0:
            return center
        elif len(center) == 0:
            return left
        else:
            raise ValueError(f"{left} {center} {right}")

    return [
        (s.group(1), s.group(2), get_phoneme(s.group(3), s.group(4), s.group(5)))
        for s in map(lambda x: r.search(x.rstrip("\r")), raw_output)
        if s is not None
    ]


def frame_to_second(time_list: List[Tuple[str, str, str]]):
    return [
        (
            f"{int(start) * 0.01 + (0.0125 if i > 0 else 0):.4f}",
            f"{(int(end) + 1) * 0.01 + 0.0125:.4f}",
            phoneme,
        )
        for i, (start, end, phoneme) in enumerate(time_list)
    ]
