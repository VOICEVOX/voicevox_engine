"""モーフィングのテスト。"""

from fastapi.testclient import TestClient


def test_モーフィング可能なスタイルとモーフィングできる(client: TestClient) -> None:
    base_style_id = 0

    # モーフィング可能なスタイルを取得する
    morphable_targets_res = client.post("/morphable_targets", json=[base_style_id])
    assert morphable_targets_res.status_code == 200
    morphable_targets = morphable_targets_res.json()[0]
    target_style_ids = [
        int(style_id)
        for style_id, info in morphable_targets.items()
        if info["is_morphable"] and int(style_id) != base_style_id
    ]
    assert len(target_style_ids) > 0

    # 取得したスタイルとモーフィングして音声を合成できる
    audio_query = client.post(
        "/audio_query", params={"text": "テストです", "speaker": base_style_id}
    ).json()
    synthesis_res = client.post(
        "/synthesis_morphing",
        params={
            "base_speaker": base_style_id,
            "target_speaker": target_style_ids[0],
            "morph_rate": 0.5,
        },
        json=audio_query,
    )
    assert synthesis_res.status_code == 200
    assert synthesis_res.headers["content-type"] == "audio/wav"
