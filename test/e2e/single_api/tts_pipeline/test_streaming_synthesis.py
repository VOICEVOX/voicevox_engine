"""/streaming_synthesis API のテスト。"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.e2e.single_api.utils import gen_mora
from test.utility import hash_wave_floats_from_wav_bytes


def _parse_multipart_response(
    content_type: str, body: bytes
) -> list[tuple[dict[str, str], bytes]]:
    boundary = content_type.split("boundary=", maxsplit=1)[1].strip('"')
    boundary_line = f"--{boundary}\r\n".encode("ascii")
    closing_boundary_line = f"--{boundary}--\r\n".encode("ascii")
    parts: list[tuple[dict[str, str], bytes]] = []
    cursor = 0

    while True:
        if body[cursor:].startswith(closing_boundary_line):
            return parts

        assert body[cursor:].startswith(boundary_line)
        cursor += len(boundary_line)

        header_end = body.index(b"\r\n\r\n", cursor)
        header_lines = body[cursor:header_end].decode("ascii").split("\r\n")
        headers: dict[str, str] = {}
        for line in header_lines:
            key, value = line.split(":", maxsplit=1)
            headers[key.lower()] = value.strip()

        content_length = int(headers["content-length"])
        body_start = header_end + len(b"\r\n\r\n")
        body_end = body_start + content_length
        parts.append((headers, body[body_start:body_end]))
        cursor = body_end + len(b"\r\n")


def test_post_streaming_synthesis_200(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    query = {
        "accent_phrases": [
            {
                "moras": [
                    gen_mora("テ", "t", 2.3, "e", 0.8, 3.3),
                    gen_mora("ス", "s", 2.1, "U", 0.3, 0.0),
                    gen_mora("ト", "t", 2.3, "o", 1.8, 4.1),
                ],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            }
        ],
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": "テ'_スト",
    }
    response = client.post(
        "/streaming_synthesis",
        params={"speaker": 0, "chunk_min_accent_phrases": 1},
        json=query,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed")

    parts = _parse_multipart_response(response.headers["content-type"], response.read())
    assert len(parts) == 1

    headers, wav_bytes = parts[0]
    assert headers["x-sequence"] == "0"
    assert headers["x-is-last"] == "true"
    assert headers["content-type"] == "audio/wav"
    assert wav_bytes.startswith(b"RIFF")
    assert snapshot == hash_wave_floats_from_wav_bytes(wav_bytes)


def test_post_streaming_synthesis_splits_by_accent_phrase(
    client: TestClient,
) -> None:
    query = {
        "accent_phrases": [
            {
                "moras": [
                    gen_mora("テ", "t", 2.3, "e", 0.8, 3.3),
                ],
                "accent": 1,
                "pause_mora": gen_mora("、", None, None, "pau", 0.3, 0.0),
                "is_interrogative": False,
            },
            {
                "moras": [
                    gen_mora("ス", "s", 2.1, "U", 0.3, 0.0),
                    gen_mora("ト", "t", 2.3, "o", 1.8, 4.1),
                ],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            },
        ],
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": "テ'、ス'_ト",
    }
    response = client.post(
        "/streaming_synthesis",
        params={"speaker": 0, "chunk_min_accent_phrases": 1},
        json=query,
    )
    assert response.status_code == 200

    parts = _parse_multipart_response(response.headers["content-type"], response.read())
    assert [headers["x-sequence"] for headers, _wav_bytes in parts] == ["0", "1"]
    assert [headers["x-is-last"] for headers, _wav_bytes in parts] == ["false", "true"]

    for _headers, wav_bytes in parts:
        assert wav_bytes.startswith(b"RIFF")


def test_post_streaming_synthesis_groups_by_chunk_min_accent_phrases(
    client: TestClient,
) -> None:
    query = {
        "accent_phrases": [
            {
                "moras": [gen_mora("テ", "t", 2.3, "e", 0.8, 3.3)],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            },
            {
                "moras": [gen_mora("ス", "s", 2.1, "U", 0.3, 0.0)],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            },
            {
                "moras": [gen_mora("ト", "t", 2.3, "o", 1.8, 4.1)],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            },
        ],
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": "テ'/ス'_ト",
    }
    response = client.post(
        "/streaming_synthesis",
        params={"speaker": 0, "chunk_min_accent_phrases": 2},
        json=query,
    )
    assert response.status_code == 200

    parts = _parse_multipart_response(response.headers["content-type"], response.read())
    assert [headers["x-sequence"] for headers, _wav_bytes in parts] == ["0", "1"]
    assert [headers["x-is-last"] for headers, _wav_bytes in parts] == ["false", "true"]

    for _headers, wav_bytes in parts:
        assert wav_bytes.startswith(b"RIFF")


def test_post_streaming_synthesis_empty_accent_phrases(
    client: TestClient,
) -> None:
    query = {
        "accent_phrases": [],
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": "",
    }
    response = client.post(
        "/streaming_synthesis",
        params={"speaker": 0, "chunk_min_accent_phrases": 1},
        json=query,
    )
    assert response.status_code == 200

    parts = _parse_multipart_response(response.headers["content-type"], response.read())
    assert len(parts) == 1

    headers, wav_bytes = parts[0]
    assert headers["x-sequence"] == "0"
    assert headers["x-is-last"] == "true"
    assert headers["content-type"] == "audio/wav"
    assert wav_bytes.startswith(b"RIFF")
