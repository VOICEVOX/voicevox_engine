"""ユーザー辞書機能を提供する API Router"""

import traceback
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import ValidationError

from voicevox_engine.model import UserDictWord
from voicevox_engine.user_dict.part_of_speech_data import (
    MAX_PRIORITY,
    MIN_PRIORITY,
    WordTypes,
)
from voicevox_engine.user_dict.user_dict import UserDictInputError, UserDictionary

from ..dependencies import check_disabled_mutable_api


def generate_user_dict_router(user_dict: UserDictionary) -> APIRouter:
    """ユーザー辞書 API Router を生成する"""
    router = APIRouter()

    @router.get(
        "/user_dict",
        response_description="単語のUUIDとその詳細",
        tags=["ユーザー辞書"],
    )
    def get_user_dict_words() -> dict[str, UserDictWord]:
        """
        ユーザー辞書に登録されている単語の一覧を返します。
        単語の表層形(surface)は正規化済みの物を返します。
        """
        try:
            return user_dict.read_dict()
        except UserDictInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="辞書の読み込みに失敗しました。"
            )

    @router.post(
        "/user_dict_word",
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def add_user_dict_word(
        surface: Annotated[str, Query(description="言葉の表層形")],
        pronunciation: Annotated[str, Query(description="言葉の発音（カタカナ）")],
        accent_type: Annotated[
            int, Query(description="アクセント型（音が下がる場所を指す）")
        ],
        word_type: Annotated[
            WordTypes | None,
            Query(
                description="PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか"
            ),
        ] = None,
        priority: Annotated[
            int | None,
            Query(
                ge=MIN_PRIORITY,
                le=MAX_PRIORITY,
                description="単語の優先度（0から10までの整数）。数字が大きいほど優先度が高くなる。1から9までの値を指定することを推奨",
            ),
        ] = None,
    ) -> str:
        """
        ユーザー辞書に言葉を追加します。
        """
        try:
            word_uuid = user_dict.apply_word(
                surface=surface,
                pronunciation=pronunciation,
                accent_type=accent_type,
                word_type=word_type,
                priority=priority,
            )
            return word_uuid
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail="パラメータに誤りがあります。\n" + str(e)
            )
        except UserDictInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="ユーザー辞書への追加に失敗しました。"
            )

    @router.put(
        "/user_dict_word/{word_uuid}",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def rewrite_user_dict_word(
        surface: Annotated[str, Query(description="言葉の表層形")],
        pronunciation: Annotated[str, Query(description="言葉の発音（カタカナ）")],
        accent_type: Annotated[
            int, Query(description="アクセント型（音が下がる場所を指す）")
        ],
        word_uuid: Annotated[str, Path(description="更新する言葉のUUID")],
        word_type: Annotated[
            WordTypes | None,
            Query(
                description="PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか"
            ),
        ] = None,
        priority: Annotated[
            int | None,
            Query(
                ge=MIN_PRIORITY,
                le=MAX_PRIORITY,
                description="単語の優先度（0から10までの整数）。数字が大きいほど優先度が高くなる。1から9までの値を指定することを推奨。",
            ),
        ] = None,
    ) -> None:
        """
        ユーザー辞書に登録されている言葉を更新します。
        """
        try:
            user_dict.rewrite_word(
                surface=surface,
                pronunciation=pronunciation,
                accent_type=accent_type,
                word_uuid=word_uuid,
                word_type=word_type,
                priority=priority,
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail="パラメータに誤りがあります。\n" + str(e)
            )
        except UserDictInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="ユーザー辞書の更新に失敗しました。"
            )

    @router.delete(
        "/user_dict_word/{word_uuid}",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def delete_user_dict_word(
        word_uuid: Annotated[str, Path(description="削除する言葉のUUID")]
    ) -> None:
        """
        ユーザー辞書に登録されている言葉を削除します。
        """
        try:
            user_dict.delete_word(word_uuid=word_uuid)
        except UserDictInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="ユーザー辞書の更新に失敗しました。"
            )

    @router.post(
        "/import_user_dict",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def import_user_dict_words(
        import_dict_data: Annotated[
            dict[str, UserDictWord],
            Body(description="インポートするユーザー辞書のデータ"),
        ],
        override: Annotated[
            bool, Query(description="重複したエントリがあった場合、上書きするかどうか")
        ],
    ) -> None:
        """
        他のユーザー辞書をインポートします。
        """
        try:
            user_dict.import_user_dict(dict_data=import_dict_data, override=override)
        except UserDictInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="ユーザー辞書のインポートに失敗しました。"
            )

    return router
