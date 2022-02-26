import json
import sys
import traceback
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict
from uuid import UUID, uuid4

import pyopenjtalk
from appdirs import user_data_dir
from fastapi import HTTPException

from .model import UserDictWord
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
    json.dump(
        user_dict, user_dict_path.open(mode="w", encoding="utf-8"), ensure_ascii=False
    )


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
                "{},1348,1348,{},{},{},{},{},{},{},{},{},{},{}/{},{}\n".format(
                    word.surface,
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
        try:
            return {
                str(UUID(word_uuid)): UserDictWord(**word)
                for word_uuid, word in json.load(f).items()
            }
        except json.decoder.JSONDecodeError:
            traceback.print_exc()
            return {}


def create_word(surface: str, pronunciation: str, accent_type: int) -> UserDictWord:
    return UserDictWord(
        surface=surface,
        cost=8600,
        part_of_speech="名詞",
        part_of_speech_detail_1="固有名詞",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
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
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    word = create_word(
        surface=surface, pronunciation=pronunciation, accent_type=accent_type
    )
    user_dict = read_dict(user_dict_path=user_dict_path)
    user_dict[str(uuid4())] = word
    write_to_json(user_dict, user_dict_path)
    update_dict(compiled_dict_path=compiled_dict_path)


def rewrite_word(
    word_uuid: str,
    surface: str,
    pronunciation: str,
    accent_type: int,
    user_dict_path: Path = user_dict_path,
    compiled_dict_path: Path = compiled_dict_path,
):
    word = create_word(
        surface=surface, pronunciation=pronunciation, accent_type=accent_type
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
