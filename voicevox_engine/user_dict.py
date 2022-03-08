import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Optional
from uuid import UUID, uuid4

import pyopenjtalk
from appdirs import user_data_dir
from fastapi import HTTPException

from .model import UserDictWord
from .part_of_speech_data import MAX_PRIORITY, MIN_PRIORITY, part_of_speech_data
from .utility import engine_root

root_dir = engine_root()
# FIXME: ファイル保存場所をエンジン固有のIDが入ったものにする
save_dir = Path(user_data_dir("voicevox-engine"))

if not save_dir.is_dir():
    save_dir.mkdir(parents=True)

default_dict_path = root_dir / "default.csv"
user_dict_path = save_dir / "user_dict.json"
compiled_dict_path = save_dir / "user.dic"


def write_to_json(user_dict: Dict[str, UserDictWord], user_dict_path: Path):
    user_dict = {word_uuid: word.dict() for word_uuid, word in user_dict.items()}
    # 予めjsonに変換できることを確かめる
    user_dict_json = json.dumps(user_dict, ensure_ascii=False)
    user_dict_path.write_text(user_dict_json, encoding="utf-8")


def user_dict_startup_processing(
    default_dict_path: Path = default_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    if not compiled_dict_path.is_file():
        pyopenjtalk.create_user_dict(
            str(default_dict_path.resolve(strict=True)),
            str(compiled_dict_path.resolve()),
        )
    pyopenjtalk.set_user_dict(str(compiled_dict_path.resolve(strict=True)))


def update_dict(
    default_dict_path: Path = default_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    with NamedTemporaryFile(encoding="utf-8", mode="w", delete=False) as f:
        if not default_dict_path.is_file():
            print("Warning: Cannot find default dictionary.", file=sys.stderr)
            return
        default_dict = default_dict_path.read_text(encoding="utf-8")
        if default_dict == default_dict.rstrip():
            default_dict += "\n"
        f.write(default_dict)
        user_dict = read_dict()
        for word_uuid in user_dict:
            word = user_dict[word_uuid]
            f.write(
                "{},{},{},{},{},{},{},{},{},{},{},{},{},{}/{},{}\n".format(
                    word.surface,
                    word.context_id,
                    word.context_id,
                    word.cost,
                    word.part_of_speech,
                    word.part_of_speech_detail_1,
                    word.part_of_speech_detail_2,
                    word.part_of_speech_detail_3,
                    word.inflectional_type,
                    word.inflectional_form,
                    word.stem,
                    word.yomi,
                    word.pronunciation,
                    word.accent_type,
                    word.mora_count,
                    word.accent_associative_rule,
                )
            )
    tmp_dict_path = Path(NamedTemporaryFile(delete=False).name).resolve()
    pyopenjtalk.create_user_dict(
        str(Path(f.name).resolve(strict=True)),
        str(tmp_dict_path),
    )
    if not tmp_dict_path.is_file():
        raise RuntimeError("辞書のコンパイル時にエラーが発生しました。")
    pyopenjtalk.unset_user_dict()
    try:
        tmp_dict_path.replace(compiled_dict_path)
    finally:
        if compiled_dict_path.is_file():
            pyopenjtalk.set_user_dict(str(compiled_dict_path.resolve(strict=True)))


def read_dict(user_dict_path: Path = user_dict_path) -> Dict[str, UserDictWord]:
    if not user_dict_path.is_file():
        return {}
    with user_dict_path.open(encoding="utf-8") as f:
        return {
            str(UUID(word_uuid)): UserDictWord(**word)
            for word_uuid, word in json.load(f).items()
        }


def create_word(
    surface: str,
    pronunciation: str,
    accent_type: int,
    word_type: Optional[str] = None,
    priority: Optional[int] = None,
) -> UserDictWord:
    if word_type is None:
        word_type = "固有名詞"
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
        cost=pos_detail.cost_candidates[MAX_PRIORITY - priority],
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
    word_type: Optional[str] = None,
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
    update_dict(compiled_dict_path=compiled_dict_path)
    return word_uuid


def rewrite_word(
    word_uuid: str,
    surface: str,
    pronunciation: str,
    accent_type: int,
    word_type: Optional[str] = None,
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
    update_dict(compiled_dict_path=compiled_dict_path)


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
    update_dict(compiled_dict_path=compiled_dict_path)
