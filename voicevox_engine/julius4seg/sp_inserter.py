import os
import re
import sys
import subprocess
from itertools import chain
from pathlib import Path, PurePath

from logging import getLogger, DEBUG, NullHandler

logger = getLogger(__name__)
logger.addHandler(NullHandler())
logger.setLevel(DEBUG)
logger.propagate = False

# MUST CHANGE
JULIUS_ROOT = PurePath('.')


def get_echo_para(filename: str) -> list:
    """ Get parameters of echo referencing platforms
    Returns:
        list[str]: echo parameters
    """
    if sys.platform.startswith("win") or sys.platform.startswith('cygwin'):
        return ["cmd.exe", "/c", "echo", filename]
    else:
        return ["echo", filename]


def get_os_dependent_directory() -> str:
    """Juluis Segmentaion-Kitのディレクトリ名をOSの種類から取得
    returns:
        (str): OS依存のパスの一部
    """
    if sys.platform.startswith('win') or sys.platform.startswith('cygwin'):
        return 'windows'
    elif sys.platform.startswith('darwin'):
        return 'osx'
    elif sys.platform.startswith('linux'):
        return 'linux'


def get_os_dependent_exec() -> str:
    """Juliusの実行ファイル名を取得
    returns:
        (str): Juliusの実行ファイル名
    """
    if sys.platform.startswith('win') or sys.platform.startswith('cygwin'):
        return 'julius.exe'
    else:
        return 'julius'


def kata2hira(kana: str) -> str:
    """ヴ，ヵ，ヶ以外のカタカナをひらがなに変換
    args:
        kana(str): カタカナ文字列
            "ヤキニク"
    returns:
        (str): ひらがな文字列
            "やきにく"
    """
    return ''.join([chr(ord(c) + ord('あ') - ord('ア')) if c != 'ー' else 'ー' for c in kana])


def conv2julius(s: str) -> str:
    """入力の単語の読み（ひらがな）をJuliusの音素列に変換
    args:
        kana(str): カタカナ文字列
            "やきにく"
    returns:
        (str): ひらがな文字列
            " y a k i n i k u"
    """
    s = s.replace('あぁ', ' a a')
    s = s.replace('いぃ', ' i i')
    s = s.replace('いぇ', ' i e')
    s = s.replace('いゃ', ' y a')
    s = s.replace('うぅ', ' u:')
    s = s.replace('えぇ', ' e e')
    s = s.replace('おぉ', ' o:')
    s = s.replace('かぁ', ' k a:')
    s = s.replace('きぃ', ' k i:')
    s = s.replace('くぅ', ' k u:')
    s = s.replace('くゃ', ' ky a')
    s = s.replace('くゅ', ' ky u')
    s = s.replace('くょ', ' ky o')
    s = s.replace('けぇ', ' k e:')
    s = s.replace('こぉ', ' k o:')
    s = s.replace('がぁ', ' g a:')
    s = s.replace('ぎぃ', ' g i:')
    s = s.replace('ぐぅ', ' g u:')
    s = s.replace('ぐゃ', ' gy a')
    s = s.replace('ぐゅ', ' gy u')
    s = s.replace('ぐょ', ' gy o')
    s = s.replace('げぇ', ' g e:')
    s = s.replace('ごぉ', ' g o:')
    s = s.replace('さぁ', ' s a:')
    s = s.replace('しぃ', ' sh i:')
    s = s.replace('すぅ', ' s u:')
    s = s.replace('すゃ', ' sh a')
    s = s.replace('すゅ', ' sh u')
    s = s.replace('すょ', ' sh o')
    s = s.replace('せぇ', ' s e:')
    s = s.replace('そぉ', ' s o:')
    s = s.replace('ざぁ', ' z a:')
    s = s.replace('じぃ', ' j i:')
    s = s.replace('ずぅ', ' z u:')
    s = s.replace('ずゃ', ' zy a')
    s = s.replace('ずゅ', ' zy u')
    s = s.replace('ずょ', ' zy o')
    s = s.replace('ぜぇ', ' z e:')
    s = s.replace('ぞぉ', ' z o:')
    s = s.replace('たぁ', ' t a:')
    s = s.replace('ちぃ', ' ch i:')
    s = s.replace('つぁ', ' ts a')
    s = s.replace('つぃ', ' ts i')
    s = s.replace('つぅ', ' ts u:')
    s = s.replace('つゃ', ' ch a')
    s = s.replace('つゅ', ' ch u')
    s = s.replace('つょ', ' ch o')
    s = s.replace('つぇ', ' ts e')
    s = s.replace('つぉ', ' ts o')
    s = s.replace('てぇ', ' t e:')
    s = s.replace('とぉ', ' t o:')
    s = s.replace('だぁ', ' d a:')
    s = s.replace('ぢぃ', ' j i:')
    s = s.replace('づぅ', ' d u:')
    s = s.replace('づゃ', ' zy a')
    s = s.replace('づゅ', ' zy u')
    s = s.replace('づょ', ' zy o')
    s = s.replace('でぇ', ' d e:')
    s = s.replace('どぉ', ' d o:')
    s = s.replace('なぁ', ' n a:')
    s = s.replace('にぃ', ' n i:')
    s = s.replace('ぬぅ', ' n u:')
    s = s.replace('ぬゃ', ' ny a')
    s = s.replace('ぬゅ', ' ny u')
    s = s.replace('ぬょ', ' ny o')
    s = s.replace('ねぇ', ' n e:')
    s = s.replace('のぉ', ' n o:')
    s = s.replace('はぁ', ' h a:')
    s = s.replace('ひぃ', ' h i:')
    s = s.replace('ふぅ', ' f u:')
    s = s.replace('ふゃ', ' hy a')
    s = s.replace('ふゅ', ' hy u')
    s = s.replace('ふょ', ' hy o')
    s = s.replace('へぇ', ' h e:')
    s = s.replace('ほぉ', ' h o:')
    s = s.replace('ばぁ', ' b a:')
    s = s.replace('びぃ', ' b i:')
    s = s.replace('ぶぅ', ' b u:')
    s = s.replace('ふゃ', ' hy a')
    s = s.replace('ぶゅ', ' by u')
    s = s.replace('ふょ', ' hy o')
    s = s.replace('べぇ', ' b e:')
    s = s.replace('ぼぉ', ' b o:')
    s = s.replace('ぱぁ', ' p a:')
    s = s.replace('ぴぃ', ' p i:')
    s = s.replace('ぷぅ', ' p u:')
    s = s.replace('ぷゃ', ' py a')
    s = s.replace('ぷゅ', ' py u')
    s = s.replace('ぷょ', ' py o')
    s = s.replace('ぺぇ', ' p e:')
    s = s.replace('ぽぉ', ' p o:')
    s = s.replace('まぁ', ' m a:')
    s = s.replace('みぃ', ' m i:')
    s = s.replace('むぅ', ' m u:')
    s = s.replace('むゃ', ' my a')
    s = s.replace('むゅ', ' my u')
    s = s.replace('むょ', ' my o')
    s = s.replace('めぇ', ' m e:')
    s = s.replace('もぉ', ' m o:')
    s = s.replace('やぁ', ' y a:')
    s = s.replace('ゆぅ', ' y u:')
    s = s.replace('ゆゃ', ' y a:')
    s = s.replace('ゆゅ', ' y u:')
    s = s.replace('ゆょ', ' y o:')
    s = s.replace('よぉ', ' y o:')
    s = s.replace('らぁ', ' r a:')
    s = s.replace('りぃ', ' r i:')
    s = s.replace('るぅ', ' r u:')
    s = s.replace('るゃ', ' ry a')
    s = s.replace('るゅ', ' ry u')
    s = s.replace('るょ', ' ry o')
    s = s.replace('れぇ', ' r e:')
    s = s.replace('ろぉ', ' r o:')
    s = s.replace('わぁ', ' w a:')
    s = s.replace('をぉ', ' o:')

    s = s.replace('ゔ', ' b u')
    s = s.replace('でぃ', ' d i')
    s = s.replace('でぇ', ' d e:')
    s = s.replace('でゃ', ' dy a')
    s = s.replace('でゅ', ' dy u')
    s = s.replace('でょ', ' dy o')
    s = s.replace('てぃ', ' t i')
    s = s.replace('てぇ', ' t e:')
    s = s.replace('てゃ', ' ty a')
    s = s.replace('てゅ', ' ty u')
    s = s.replace('てょ', ' ty o')
    s = s.replace('すぃ', ' s i')
    s = s.replace('ずぁ', ' z u a')
    s = s.replace('ずぃ', ' z i')
    s = s.replace('ずぅ', ' z u')
    s = s.replace('ずゃ', ' zy a')
    s = s.replace('ずゅ', ' zy u')
    s = s.replace('ずょ', ' zy o')
    s = s.replace('ずぇ', ' z e')
    s = s.replace('ずぉ', ' z o')
    s = s.replace('きゃ', ' ky a')
    s = s.replace('きゅ', ' ky u')
    s = s.replace('きょ', ' ky o')
    s = s.replace('しゃ', ' sh a')
    s = s.replace('しゅ', ' sh u')
    s = s.replace('しぇ', ' sh e')
    s = s.replace('しょ', ' sh o')
    s = s.replace('ちゃ', ' ch a')
    s = s.replace('ちゅ', ' ch u')
    s = s.replace('ちぇ', ' ch e')
    s = s.replace('ちょ', ' ch o')
    s = s.replace('とぅ', ' t u')
    s = s.replace('とゃ', ' ty a')
    s = s.replace('とゅ', ' ty u')
    s = s.replace('とょ', ' ty o')
    s = s.replace('どぁ', ' d o a')
    s = s.replace('どぅ', ' d u')
    s = s.replace('どゃ', ' dy a')
    s = s.replace('どゅ', ' dy u')
    s = s.replace('どょ', ' dy o')
    s = s.replace('どぉ', ' d o:')
    s = s.replace('にゃ', ' ny a')
    s = s.replace('にゅ', ' ny u')
    s = s.replace('にょ', ' ny o')
    s = s.replace('ひゃ', ' hy a')
    s = s.replace('ひゅ', ' hy u')
    s = s.replace('ひょ', ' hy o')
    s = s.replace('みゃ', ' my a')
    s = s.replace('みゅ', ' my u')
    s = s.replace('みょ', ' my o')
    s = s.replace('りゃ', ' ry a')
    s = s.replace('りゅ', ' ry u')
    s = s.replace('りょ', ' ry o')
    s = s.replace('ぎゃ', ' gy a')
    s = s.replace('ぎゅ', ' gy u')
    s = s.replace('ぎょ', ' gy o')
    s = s.replace('ぢぇ', ' j e')
    s = s.replace('ぢゃ', ' j a')
    s = s.replace('ぢゅ', ' j u')
    s = s.replace('ぢょ', ' j o')
    s = s.replace('じぇ', ' j e')
    s = s.replace('じゃ', ' j a')
    s = s.replace('じゅ', ' j u')
    s = s.replace('じょ', ' j o')
    s = s.replace('びゃ', ' by a')
    s = s.replace('びゅ', ' by u')
    s = s.replace('びょ', ' by o')
    s = s.replace('ぴゃ', ' py a')
    s = s.replace('ぴゅ', ' py u')
    s = s.replace('ぴょ', ' py o')
    s = s.replace('うぁ', ' u a')
    s = s.replace('うぃ', ' w i')
    s = s.replace('うぇ', ' w e')
    s = s.replace('うぉ', ' w o')
    s = s.replace('ふぁ', ' f a')
    s = s.replace('ふぃ', ' f i')
    s = s.replace('ふぅ', ' f u')
    s = s.replace('ふゃ', ' hy a')
    s = s.replace('ふゅ', ' hy u')
    s = s.replace('ふょ', ' hy o')
    s = s.replace('ふぇ', ' f e')
    s = s.replace('ふぉ', ' f o')

    # 1音からなる変換規則
    s = s.replace('あ', ' a')
    s = s.replace('い', ' i')
    s = s.replace('う', ' u')
    s = s.replace('え', ' e')
    s = s.replace('お', ' o')
    s = s.replace('か', ' k a')
    s = s.replace('き', ' k i')
    s = s.replace('く', ' k u')
    s = s.replace('け', ' k e')
    s = s.replace('こ', ' k o')
    s = s.replace('さ', ' s a')
    s = s.replace('し', ' sh i')
    s = s.replace('す', ' s u')
    s = s.replace('せ', ' s e')
    s = s.replace('そ', ' s o')
    s = s.replace('た', ' t a')
    s = s.replace('ち', ' ch i')
    s = s.replace('つ', ' ts u')
    s = s.replace('て', ' t e')
    s = s.replace('と', ' t o')
    s = s.replace('な', ' n a')
    s = s.replace('に', ' n i')
    s = s.replace('ぬ', ' n u')
    s = s.replace('ね', ' n e')
    s = s.replace('の', ' n o')
    s = s.replace('は', ' h a')
    s = s.replace('ひ', ' h i')
    s = s.replace('ふ', ' f u')
    s = s.replace('へ', ' h e')
    s = s.replace('ほ', ' h o')
    s = s.replace('ま', ' m a')
    s = s.replace('み', ' m i')
    s = s.replace('む', ' m u')
    s = s.replace('め', ' m e')
    s = s.replace('も', ' m o')
    s = s.replace('ら', ' r a')
    s = s.replace('り', ' r i')
    s = s.replace('る', ' r u')
    s = s.replace('れ', ' r e')
    s = s.replace('ろ', ' r o')
    s = s.replace('が', ' g a')
    s = s.replace('ぎ', ' g i')
    s = s.replace('ぐ', ' g u')
    s = s.replace('げ', ' g e')
    s = s.replace('ご', ' g o')
    s = s.replace('ざ', ' z a')
    s = s.replace('じ', ' j i')
    s = s.replace('ず', ' z u')
    s = s.replace('ぜ', ' z e')
    s = s.replace('ぞ', ' z o')
    s = s.replace('だ', ' d a')
    s = s.replace('ぢ', ' j i')
    s = s.replace('づ', ' z u')
    s = s.replace('で', ' d e')
    s = s.replace('ど', ' d o')
    s = s.replace('ば', ' b a')
    s = s.replace('び', ' b i')
    s = s.replace('ぶ', ' b u')
    s = s.replace('べ', ' b e')
    s = s.replace('ぼ', ' b o')
    s = s.replace('ぱ', ' p a')
    s = s.replace('ぴ', ' p i')
    s = s.replace('ぷ', ' p u')
    s = s.replace('ぺ', ' p e')
    s = s.replace('ぽ', ' p o')
    s = s.replace('や', ' y a')
    s = s.replace('ゆ', ' y u')
    s = s.replace('よ', ' y o')
    s = s.replace('わ', ' w a')
    s = s.replace('を', ' o')
    s = s.replace('ん', ' N')
    s = s.replace('っ', ' q')
    s = s.replace('ー', ':')

    s = s.replace('ぁ', ' a')
    s = s.replace('ぃ', ' i')
    s = s.replace('ぅ', ' u')
    s = s.replace('ぇ', ' e')
    s = s.replace('ぉ', ' o')
    s = s.replace('ゎ', ' w a')

    s = s[1:]

    s = re.sub(r':+', ':', s)

    return s


def gen_julius_dict_1st(text_symbols: [str], word_phones: [str]) -> str:
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
        tmp.append('{}\t[{}]\t{}'.format(i * 2, *zipped))
        if i + 1 != finit:
            tmp.append('{}\t[{}]\t{}'.format(i * 2 + 1, 'sp_{}'.format(i), 'sp'))

    # append sp and Start, End symbol
    tmp.append('{}\t[{}]\t{}'.format(i * 2 + 1, '<s>', 'silB'))
    tmp.append('{}\t[{}]\t{}'.format((i + 1) * 2, '</s>', 'silE'))

    return '\n'.join(tmp) + '\n'


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
            tmp.append('{} {} {} {} {}'.format(i, number_of_words - 1, i + 1, 0, 1))
            i += 1
        elif i > 0 and not isLast:
            tmp.append('{} {} {} {} {}'.format(i, current_word, i + 1, 0, 0))
            current_word -= 1
            isLast = current_word == -1
            i += 1
        elif i > 0 and isLast:
            tmp.append('{} {} {} {} {}'.format(i, i - 1, i + 1, 0, 0))
            tmp.append('{} {} {} {} {}'.format(i + 1, -1, -1, 1, 0))
            break

    return '\n'.join(tmp) + '\n'


def gen_julius_dict_2nd(phone_seqence: str) -> str:
    """音素系列から強制アライメントのためのdictファイルの中身を生成
    args:
        phone_seqence (str):
            'k o N k a i w a '
    returns:
        (str): Juliusのdictファイルの中身
    """
    return '\n'.join([
        '0\t[w_0]\tsilB',
        '1\t[w_1]\t{}'.format(phone_seqence),
        '2\t[w_2]\tsilE',
    ]) + '\n'


def gen_julius_aliment_dfa() -> str:
    """強制アライメント用のdfaファイルの中身を生成
    returns:
        (str): Juliusのdfaファイルの中身
    """
    return '\n'.join([
        '0 2 1 0 1',
        '1 1 2 0 0',
        '2 0 3 0 0',
        '3 -1 -1 1 0'
    ]) + '\n'


def julius_sp_insert(target_wav_file: str, aliment_file_signiture: str, model_path: str = None) -> [str]:
    julius_args = {
        '-h': str(
            JULIUS_ROOT / 'model' / 'phone_m' / 'jnas-mono-16mix-gid.binhmm'
        ) if model_path is None else model_path,
        '-input': 'file',
        '-debug': '',
        '-gram': aliment_file_signiture,
    }

    file_echo_p = subprocess.Popen(get_echo_para(target_wav_file), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    julius_p = subprocess.Popen(' '.join([str(JULIUS_ROOT / 'bin' / get_os_dependent_directory() / get_os_dependent_exec()),
                                          *list(chain.from_iterable([[k, v] for k, v in julius_args.items()]))]).split(), stdin=file_echo_p.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    file_echo_p.stdout.close()
    return julius_p.communicate()[0].decode('utf-8').split('\n')


def get_sp_inserted_text(raw_output: str, debug_symbol='') -> (str, [int]):
    """デコード結果からsp挿入後のテキストとspのインデックスを取得する
    args:
        raw_output: `julius_sp_insert`の出力
    returns:
        Tuple(str, [int]): デコード結果とspのindex
    """
    r = re.compile('<s> (.*) </s>')
    pass1_best = next(s for s in raw_output if s.startswith('pass1_best'))
    matched = r.search(pass1_best)
    if matched is None:
        logger.warning('Failed Decoding Text [{}]'.format(debug_symbol))
        raise Exception("Decode Failed")

    return (re.sub('sp_[\d+]', '<sp>', matched.group(1)), [int(s.split('_')[1]) for s in matched.group().split() if 'sp_' in s])


def get_sp_inserterd_phone_seqence(raw_output: str, debug_symbol='') -> str:
    pass1_best_phonemeseq = next(s for s in raw_output if s.startswith('pass1_best_phonemeseq'))

    complete_re = re.compile('silB \| (.*) \| silE')
    failed_re_1 = re.compile('silE \| (.*) \| silB')
    failed_re_2 = re.compile('silE \| (.*)')

    if complete_re.search(pass1_best_phonemeseq) is not None:
        matched = complete_re.search(pass1_best_phonemeseq)
    elif failed_re_1.search(pass1_best_phonemeseq) is not None:
        logger.info('Use not correct re to generate Phoneseq [{}]'.format(debug_symbol))
        matched = failed_re_1.search(pass1_best_phonemeseq)
    elif failed_re_2.search(pass1_best_phonemeseq) is not None:
        logger.info('Use not correct re to generate Phoneseq [{}]'.format(debug_symbol))
        matched = failed_re_2.search(pass1_best_phonemeseq)
    else:
        logger.warning('Failed Generate Phoneseq [{}]'.format(debug_symbol))
        raise Exception("Decode Failed")

    tmp = matched.group(1)
    return ' '.join([s.strip() for s in tmp.split('|')])


def julius_phone_alignment(target_wav_file: str, aliment_file_signiture: str, model_path: str = None) -> [str]:
    julius_args = {
        '-h': str(
            JULIUS_ROOT / 'model' / 'phone_m' / 'jnas-mono-16mix-gid.binhmm'
        ) if model_path is None else model_path,
        '-palign': '',
        '-input': 'file',
        '-gram': aliment_file_signiture,
    }

    file_echo_p = subprocess.Popen(get_echo_para(target_wav_file), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    julius_p = subprocess.Popen(' '.join([str(JULIUS_ROOT / 'bin' / get_os_dependent_directory() / get_os_dependent_exec()),
                                          *list(chain.from_iterable([[k, v] for k, v in julius_args.items()]))]).split(), stdin=file_echo_p.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    file_echo_p.stdout.close()
    return julius_p.communicate()[0].decode('utf-8').split('\n')


def get_time_alimented_list(raw_output: str) -> [str]:
    r = re.compile('\[\s*(\d+)\s+(\d+)\s*\]\s*[\-]*[\d,\.]+\s*([\w,\:]+)$')

    return [
        (s.group(1), s.group(2), s.group(3))
        for s in map(lambda x: r.search(x.rstrip("\r")), raw_output) if s is not None
    ]
