import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pyopenjtalk
from appdirs import user_data_dir

from .model import UserDictJson, UserDictWord
from .utility import engine_root

root_dir = engine_root()
save_dir = Path(user_data_dir("voicevox-engine"))

if not save_dir.is_dir():
    save_dir.mkdir(parents=True)

default_dict_path = root_dir / "default.csv"
user_dict_path = save_dir / "user_dict.json"
compiled_dict_path = save_dir / "user.dic"


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
    user_dict_path: Path = user_dict_path,
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
        for id in user_dict.words:
            word = user_dict.words[id]
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
    except Exception:
        print("Warning: 辞書の更新に失敗しました。古い辞書を使用します。", file=sys.stderr)
    finally:
        if compiled_dict_path.is_file():
            pyopenjtalk.set_user_dict(str(compiled_dict_path.resolve(strict=True)))


def read_dict(user_dict_path: Path = user_dict_path) -> UserDictJson:
    if not user_dict_path.is_file():
        return UserDictJson(**{"next_id": 0, "words": {}})
    with user_dict_path.open(encoding="utf-8") as f:
        return UserDictJson(**json.load(f))


def apply_word(**kwargs):
    if "user_dict_path" in kwargs:
        _user_dict_path = kwargs["user_dict_path"]
    else:
        _user_dict_path = user_dict_path
    word = UserDictWord(
        surface=kwargs["surface"],
        cost=8600,
        part_of_speech="名詞",
        part_of_speech_detail_1="固有名詞",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        inflectional_type="*",
        inflectional_form="*",
        stem="*",
        yomi=kwargs["pronunciation"],
        pronunciation=kwargs["pronunciation"],
        accent_type=kwargs["accent_type"],
        accent_associative_rule="*",
    )
    user_dict = read_dict(user_dict_path=_user_dict_path)
    id = user_dict.next_id
    user_dict.next_id += 1
    user_dict.words[id] = word
    with _user_dict_path.open(encoding="utf-8", mode="w") as f:
        json.dump(user_dict.dict(), f, ensure_ascii=False)
    _user_dict_path.write_text(user_dict.json(ensure_ascii=False), encoding="utf-8")
    update_dict(user_dict_path=_user_dict_path)
