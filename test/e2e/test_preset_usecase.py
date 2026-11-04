"""プリセットを使った音声合成のテスト。"""

from fastapi.testclient import TestClient


def test_登録したプリセットで音声を合成できる(client: TestClient) -> None:
    preset = {
        "id": 9999,
        "name": "テスト用プリセット",
        "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
        "style_id": 0,
        "speedScale": 1.5,
        "pitchScale": 0.1,
        "intonationScale": 1.2,
        "volumeScale": 0.8,
        "prePhonemeLength": 0.2,
        "postPhonemeLength": 0.3,
        "pauseLength": None,
        "pauseLengthScale": 1,
    }

    # プリセットを登録する
    add_res = client.post("/add_preset", json=preset)
    assert add_res.status_code == 200
    preset_id = add_res.json()

    # 登録したプリセットがプリセット一覧に含まれる
    presets = client.get("/presets").json()
    assert preset in presets

    # 登録したプリセットの値が AudioQuery に反映される
    audio_query_res = client.post(
        "/audio_query_from_preset",
        params={"text": "テストです", "preset_id": preset_id},
    )
    assert audio_query_res.status_code == 200
    audio_query = audio_query_res.json()
    for key in [
        "speedScale",
        "pitchScale",
        "intonationScale",
        "volumeScale",
        "prePhonemeLength",
        "postPhonemeLength",
    ]:
        assert audio_query[key] == preset[key]

    # プリセットから生成した AudioQuery で音声を合成できる
    synthesis_res = client.post("/synthesis", params={"speaker": 0}, json=audio_query)
    assert synthesis_res.status_code == 200
    assert synthesis_res.headers["content-type"] == "audio/wav"
