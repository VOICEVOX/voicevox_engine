import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

import pyopenjtalk

from .model import UserDictJson, UserDictWord

# nuitkaビルドをした際はグローバルに__compiled__が含まれる
if "__compiled__" in globals():
    root_dir = Path(sys.argv[0]).parent
else:
    root_dir = Path(__file__).parents[1]


default_dict_path = root_dir / "default.csv"
user_dict_path = root_dir / "user_dict.json"
compiled_dict_path = root_dir / "user.dic"

mora_prog = re.compile("(?:[アイウエオカ-モヤユヨ-ロワ-ヶ][ァィゥェォャュョヮ]|[アイウエオカ-モヤユヨ-ロワ-ヶー])")


def dict_hash(compiled_dict_path: Path = compiled_dict_path) -> Optional[str]:
    if not compiled_dict_path.is_file():
        return None
    with open(compiled_dict_path, mode="rb") as f:
        return sha256(f.read()).hexdigest()


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
        with open(default_dict_path, encoding="utf-8") as f2:
            default_dict = f2.read()
        if default_dict == default_dict.rstrip():
            default_dict += "\n"
        f.write(default_dict)
        if user_dict_path.is_file():
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
    pyopenjtalk.unset_user_dict()
    old_dict_hash = dict_hash(compiled_dict_path)
    pyopenjtalk.create_user_dict(
        str(Path(f.name).resolve(strict=True)),
        str(compiled_dict_path.resolve()),
    )
    if not compiled_dict_path.is_file():
        raise RuntimeError("辞書のコンパイル時にエラーが発生しました。")
    pyopenjtalk.set_user_dict(str(compiled_dict_path.resolve(strict=True)))
    if old_dict_hash is not None and dict_hash(compiled_dict_path) == old_dict_hash:
        raise RuntimeError("辞書のコンパイル時にエラーが発生しました。古い状態のユーザ辞書が適用されます。")


def read_dict(user_dict_path: Path = user_dict_path) -> UserDictJson:
    if not user_dict_path.is_file():
        return UserDictJson(**{"next_id": 0, "words": {}})
    with open(user_dict_path, encoding="utf-8") as f:
        return UserDictJson(**json.load(f))


def apply_checked_word(word: UserDictWord, user_dict_path: Path = user_dict_path):
    user_dict = read_dict(user_dict_path=user_dict_path)
    id = user_dict.next_id
    user_dict.next_id += 1
    user_dict.words[id] = word
    with open(user_dict_path, encoding="utf-8", mode="w") as f:
        json.dump(user_dict.dict(), f, ensure_ascii=False)
    update_dict(user_dict_path=user_dict_path)


def apply_word(**kwargs):
    if "user_dict_path" in kwargs:
        _user_dict_path = kwargs["user_dict_path"]
    else:
        _user_dict_path = user_dict_path
    apply_checked_word(
        word=UserDictWord(
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
            mora_count=len(mora_prog.findall(kwargs["pronunciation"])),
            accent_associative_rule="*",
            cost_percentile=50,
        ),
        user_dict_path=_user_dict_path,
    )
