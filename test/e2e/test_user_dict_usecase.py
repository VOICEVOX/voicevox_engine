"""ユーザー辞書を使った音声合成のテスト。"""

from fastapi.testclient import TestClient


def test_ユーザー辞書に登録した単語が読み方に反映される(client: TestClient) -> None:
    text = "藍琉です"

    # 登録前は辞書にない読み方になる
    before_kana = client.post(
        "/audio_query", params={"text": text, "speaker": 0}
    ).json()["kana"]
    assert before_kana == "ア'イ、デ'_ス"

    # ユーザー辞書に単語を登録する
    add_res = client.post(
        "/user_dict_word",
        params={"surface": "藍琉", "pronunciation": "アイル", "accent_type": 1},
    )
    assert add_res.status_code == 200
    word_uuid = add_res.json()

    try:
        # 登録した単語がユーザー辞書の一覧に含まれる
        user_dict = client.get("/user_dict").json()
        assert user_dict[word_uuid]["pronunciation"] == "アイル"

        # 登録した単語の読み方が AudioQuery に反映される
        after_kana = client.post(
            "/audio_query", params={"text": text, "speaker": 0}
        ).json()["kana"]
        assert after_kana == "ア'イルデ_ス"
    finally:
        # NOTE: ユーザー辞書は OpenJTalk 全体に適用されるため、他のテストへ影響しないよう削除する
        client.delete(f"/user_dict_word/{word_uuid}")

    # 削除すると元の読み方に戻る
    deleted_kana = client.post(
        "/audio_query", params={"text": text, "speaker": 0}
    ).json()["kana"]
    assert deleted_kana == before_kana
