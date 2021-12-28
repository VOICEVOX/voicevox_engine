import array
import struct
import wave

# 有声音素を削らないためのマージン
MARGIN = 5


def get_sp_segment(time_list: [str]) -> [[int]]:
    '''音素セグメントリストから無音区間の部分のみを抽出
    args:
        time_list ([str]): 音素セグメントリスト
    returns:
        [[int]]: 無音区間の初めと終わりのフレームのリスト
    '''
    sps = [list(map(int, s.split()[:2])) for s in time_list if 'silB' in s or 'silE' in s or 'sp' in s]
    return sps


def get_wav_sp_removed(wav_file_name: str, sp_segment: [[int]], only_edge: bool = False, start_margin: int = MARGIN, end_margin: int = MARGIN) -> [int]:
    with wave.open(wav_file_name) as f:
        n = f.getnframes()
        data = struct.unpack('h' * n, f.readframes(n))

    removed = []

    seg_start = 0

    if only_edge:
        tmp = sp_segment[0][1] * 10 - start_margin
        seg_start = tmp if tmp > 0 else sp_segment[0][0] * 10

        tmp = sp_segment[-1][0] * 10 + end_margin
        seg_end = tmp if tmp < sp_segment[-1][1] * 10 else sp_segment[-1][1] * 10

        removed.extend(data[int(seg_start / 1000 * 16000):int(seg_end / 1000 * 16000)])
    else:
        for i, seg in enumerate(sp_segment):
            if i == 0:
                seg_start = seg[1] * 10 - MARGIN  # ms
                continue

            seg_end = seg[0] * 10 + MARGIN

            removed.extend(data[int(seg_start / 1000 * 16000):int(seg_end / 1000 * 16000)])

            if i != len(sp_segment) - 1:
                seg_start = seg[1] * 10 - MARGIN

    return removed
