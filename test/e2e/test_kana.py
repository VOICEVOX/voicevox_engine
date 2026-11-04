"""AquesTalk 風記法による読み方の取得・修正のテスト。"""

from fastapi.testclient import TestClient


def test_読み方をAquesTalk風記法で取得して修正できる(client: TestClient) -> None:
    # テキストから AudioQuery を生成すると、読み方が AquesTalk 風記法で得られる
    audio_query = client.post(
        "/audio_query", params={"text": "テストです", "speaker": 0}
    ).json()
    assert audio_query["kana"] == "テ'_ストデ_ス"

    # アクセント位置を修正した読み方からアクセント句を生成する
    fixed_kana = "テスト'デ_ス"
    accent_phrases_res = client.post(
        "/accent_phrases", params={"text": fixed_kana, "speaker": 0, "is_kana": True}
    )
    assert accent_phrases_res.status_code == 200
    accent_phrases = accent_phrases_res.json()

    # 修正したアクセント位置が反映されている
    assert [accent_phrase["accent"] for accent_phrase in accent_phrases] == [3]

    # 修正したアクセント句で音声を合成できる
    audio_query["accent_phrases"] = accent_phrases
    synthesis_res = client.post("/synthesis", params={"speaker": 0}, json=audio_query)
    assert synthesis_res.status_code == 200
    assert synthesis_res.headers["content-type"] == "audio/wav"
