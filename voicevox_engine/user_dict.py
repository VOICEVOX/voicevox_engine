import json
import sys
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
import pyopenjtalk
from fastapi import HTTPException
from pydantic import conint

from .model import UserDictWord, WordTypes
from .part_of_speech_data import MAX_PRIORITY, MIN_PRIORITY, part_of_speech_data
from .utility import engine_root, get_save_dir, mutex_wrapper

root_dir = engine_root()
save_dir = get_save_dir()

if not save_dir.is_dir():
    save_dir.mkdir(parents=True)

default_dict_path = root_dir / "default.csv"
user_dict_path = save_dir / "user_dict.json"
compiled_dict_path = save_dir / "user.dic"


mutex_user_dict = threading.Lock()
mutex_openjtalk_dict = threading.Lock()


@mutex_wrapper(mutex_user_dict)
def write_to_json(user_dict: Dict[str, UserDictWord], user_dict_path: Path):
    converted_user_dict = {}
    for word_uuid, word in user_dict.items():
        word_dict = word.dict()
        word_dict["cost"] = priority2cost(
            word_dict["context_id"], word_dict["priority"]
        )
        del word_dict["priority"]
        converted_user_dict[word_uuid] = word_dict
    # 予めjsonに変換できることを確かめる
    user_dict_json = json.dumps(converted_user_dict, ensure_ascii=False)
    user_dict_path.write_text(user_dict_json, encoding="utf-8")


@mutex_wrapper(mutex_openjtalk_dict)
def update_dict(
    default_dict_path: Path = default_dict_path,
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    random_string = uuid4()
    tmp_csv_path = save_dir / f".tmp.dict_csv-{random_string}"
    tmp_compiled_path = save_dir / f".tmp.dict_compiled-{random_string}"

    try:
        # 辞書.csvを作成
        csv_text = ""
        if not default_dict_path.is_file():
            print("Warning: Cannot find default dictionary.", file=sys.stderr)
            return
        default_dict = default_dict_path.read_text(encoding="utf-8")
        if default_dict == default_dict.rstrip():
            default_dict += "\n"
        csv_text += default_dict
        user_dict = read_dict(user_dict_path=user_dict_path)
        for word_uuid in user_dict:
            word = user_dict[word_uuid]
            csv_text += (
                "{surface},{context_id},{context_id},{cost},{part_of_speech},"
                + "{part_of_speech_detail_1},{part_of_speech_detail_2},"
                + "{part_of_speech_detail_3},{inflectional_type},"
                + "{inflectional_form},{stem},{yomi},{pronunciation},"
                + "{accent_type}/{mora_count},{accent_associative_rule}\n"
            ).format(
                surface=word.surface,
                context_id=word.context_id,
                cost=priority2cost(word.context_id, word.priority),
                part_of_speech=word.part_of_speech,
                part_of_speech_detail_1=word.part_of_speech_detail_1,
                part_of_speech_detail_2=word.part_of_speech_detail_2,
                part_of_speech_detail_3=word.part_of_speech_detail_3,
                inflectional_type=word.inflectional_type,
                inflectional_form=word.inflectional_form,
                stem=word.stem,
                yomi=word.yomi,
                pronunciation=word.pronunciation,
                accent_type=word.accent_type,
                mora_count=word.mora_count,
                accent_associative_rule=word.accent_associative_rule,
            )
        tmp_csv_path.write_text(csv_text, encoding="utf-8")

        # 辞書.csvをOpenJTalk用にコンパイル
        pyopenjtalk.create_user_dict(str(tmp_csv_path), str(tmp_compiled_path))
        if not tmp_compiled_path.is_file():
            raise RuntimeError("辞書のコンパイル時にエラーが発生しました。")

        # コンパイル済み辞書の置き換え・読み込み
        pyopenjtalk.unset_user_dict()
        tmp_compiled_path.replace(compiled_dict_path)
        if compiled_dict_path.is_file():
            pyopenjtalk.set_user_dict(str(compiled_dict_path.resolve(strict=True)))

    except Exception as e:
        print("Error: Failed to update dictionary.", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise e

    finally:
        # 後処理
        if tmp_csv_path.exists():
            tmp_csv_path.unlink()
        if tmp_compiled_path.exists():
            tmp_compiled_path.unlink()


@mutex_wrapper(mutex_user_dict)
def read_dict(user_dict_path: Path = user_dict_path) -> Dict[str, UserDictWord]:
    if not user_dict_path.is_file():
        return {}
    with user_dict_path.open(encoding="utf-8") as f:
        result = {}
        for word_uuid, word in json.load(f).items():
            # cost2priorityで変換を行う際にcontext_idが必要となるが、
            # 0.12以前の辞書は、context_idがハードコーディングされていたためにユーザー辞書内に保管されていない
            # ハードコーディングされていたcontext_idは固有名詞を意味するものなので、固有名詞のcontext_idを補完する
            if word.get("context_id") is None:
                word["context_id"] = part_of_speech_data[
                    WordTypes.PROPER_NOUN
                ].context_id
            word["priority"] = cost2priority(word["context_id"], word["cost"])
            del word["cost"]
            result[str(UUID(word_uuid))] = UserDictWord(**word)

    return result


def create_word(
    surface: str,
    pronunciation: str,
    accent_type: int,
    word_type: Optional[WordTypes] = None,
    priority: Optional[int] = None,
) -> UserDictWord:
    if word_type is None:
        word_type = WordTypes.PROPER_NOUN
    if word_type not in part_of_speech_data.keys():
        raise HTTPException(status_code=422, detail="不明な品詞です")
    if priority is None:
        priority = 5
    if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise HTTPException(status_code=422, detail="優先度の値が無効です")
    pos_detail = part_of_speech_data[word_type]
    return UserDictWord(
        surface=surface,
        context_id=pos_detail.context_id,
        priority=priority,
        part_of_speech=pos_detail.part_of_speech,
        part_of_speech_detail_1=pos_detail.part_of_speech_detail_1,
        part_of_speech_detail_2=pos_detail.part_of_speech_detail_2,
        part_of_speech_detail_3=pos_detail.part_of_speech_detail_3,
        inflectional_type="*",
        inflectional_form="*",
        stem="*",
        yomi=pronunciation,
        pronunciation=pronunciation,
        accent_type=accent_type,
        accent_associative_rule="*",
    )


def apply_word(
    surface: str,
    pronunciation: str,
    accent_type: int,
    word_type: Optional[WordTypes] = None,
    priority: Optional[int] = None,
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
) -> str:
    word = create_word(
        surface=surface,
        pronunciation=pronunciation,
        accent_type=accent_type,
        word_type=word_type,
        priority=priority,
    )
    user_dict = read_dict(user_dict_path=user_dict_path)
    word_uuid = str(uuid4())
    user_dict[word_uuid] = word
    write_to_json(user_dict, user_dict_path)
    update_dict(user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path)
    return word_uuid


def rewrite_word(
    word_uuid: str,
    surface: str,
    pronunciation: str,
    accent_type: int,
    word_type: Optional[WordTypes] = None,
    priority: Optional[int] = None,
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    word = create_word(
        surface=surface,
        pronunciation=pronunciation,
        accent_type=accent_type,
        word_type=word_type,
        priority=priority,
    )
    user_dict = read_dict(user_dict_path=user_dict_path)
    if word_uuid not in user_dict:
        raise HTTPException(status_code=422, detail="UUIDに該当するワードが見つかりませんでした")
    user_dict[word_uuid] = word
    write_to_json(user_dict, user_dict_path)
    update_dict(user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path)


def delete_word(
    word_uuid: str,
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    user_dict = read_dict(user_dict_path=user_dict_path)
    if word_uuid not in user_dict:
        raise HTTPException(status_code=422, detail="IDに該当するワードが見つかりませんでした")
    del user_dict[word_uuid]
    write_to_json(user_dict, user_dict_path)
    update_dict(user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path)


def import_user_dict(
    dict_data: Dict[str, UserDictWord],
    override: bool = False,
    user_dict_path: Path = user_dict_path,
    default_dict_path: Path = default_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    # 念のため型チェックを行う
    for word_uuid, word in dict_data.items():
        UUID(word_uuid)
        assert isinstance(word, UserDictWord)
        for pos_detail in part_of_speech_data.values():
            if word.context_id == pos_detail.context_id:
                assert word.part_of_speech == pos_detail.part_of_speech
                assert (
                    word.part_of_speech_detail_1 == pos_detail.part_of_speech_detail_1
                )
                assert (
                    word.part_of_speech_detail_2 == pos_detail.part_of_speech_detail_2
                )
                assert (
                    word.part_of_speech_detail_3 == pos_detail.part_of_speech_detail_3
                )
                assert (
                    word.accent_associative_rule in pos_detail.accent_associative_rules
                )
                break
        else:
            raise ValueError("対応していない品詞です")
    old_dict = read_dict(user_dict_path=user_dict_path)
    if override:
        new_dict = {**old_dict, **dict_data}
    else:
        new_dict = {**dict_data, **old_dict}
    write_to_json(user_dict=new_dict, user_dict_path=user_dict_path)
    update_dict(
        default_dict_path=default_dict_path,
        user_dict_path=user_dict_path,
        compiled_dict_path=compiled_dict_path,
    )


def search_cost_candidates(context_id: int) -> List[int]:
    for value in part_of_speech_data.values():
        if value.context_id == context_id:
            return value.cost_candidates
    raise HTTPException(status_code=422, detail="品詞IDが不正です")


def cost2priority(context_id: int, cost: conint(ge=-32768, le=32767)) -> int:
    cost_candidates = search_cost_candidates(context_id)
    # cost_candidatesの中にある値で最も近い値を元にpriorityを返す
    # 参考: https://qiita.com/Krypf/items/2eada91c37161d17621d
    # この関数とpriority2cost関数によって、辞書ファイルのcostを操作しても最も近いpriorityのcostに上書きされる
    return MAX_PRIORITY - np.argmin(np.abs(np.array(cost_candidates) - cost))


def priority2cost(
    context_id: int, priority: conint(ge=MIN_PRIORITY, le=MAX_PRIORITY)
) -> int:
    cost_candidates = search_cost_candidates(context_id)
    return cost_candidates[MAX_PRIORITY - priority]
