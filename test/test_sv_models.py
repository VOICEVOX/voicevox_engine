import filecmp
import json
import os
import shutil
from pathlib import Path
from unittest import TestCase

from voicevox_engine.model import (
    Speaker,
    SpeakerInfo,
    SpeakerStyle,
    StyleInfo,
    SVModelInfo,
)
from voicevox_engine.sv_model import get_all_sv_models, register_sv_model


class TestSVModel(TestCase):
    def test_get_all_sv_models(self):
        stored_dir = Path("test") / "testdata"
        sv_models = get_all_sv_models(stored_dir=stored_dir)
        self.assertListEqual(
            sv_models,
            [
                "official",
                "35b2c544-660e-401e-b503-0e14c635303a",
            ],
        )

    def test_register_sv_model(self):
        # clean up directories
        if os.path.exists("./test/model"):
            shutil.rmtree("./test/model")
        if os.path.exists("./test/speaker_info"):
            shutil.rmtree("./test/speaker_info")

        # ready default librareis.json
        os.makedirs("./test/model")
        with open("./test/model/libraries.json", "w") as f:
            json.dump({"official": True}, f)

        # ready dummy data
        sv_model_uuid = "b351e601-3e98-40d4-ac1d-19529d932c22"
        speaker_uuid = "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff"
        sv_model = SVModelInfo(
            uuid=sv_model_uuid,
            variance_model="dmFyaWFuY2VfbW9kZWw=",  # variance_model
            embedder_model="ZW1iZWRkZXJfbW9kZWw=",  # embedder_model
            decoder_model="ZGVjb2Rlcl9tb2RlbA==",  # decoder_model
            metas=[
                Speaker(
                    name="小春音アミ",
                    speaker_uuid=speaker_uuid,
                    styles=[
                        SpeakerStyle(
                            name="ノーマル",
                            id=0,
                        ),
                    ],
                    version="0.0.1",
                ),
            ],
            speaker_infos={
                speaker_uuid: SpeakerInfo(
                    policy="dummy policy",
                    portrait="cG9ydHJhaXQucG5n",  # portrait.png
                    style_infos=[
                        StyleInfo(
                            id=0,
                            icon="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",  # noqa
                            voice_samples=[
                                "dm9pY2Vfc2FtcGxlMQ==",  # voice_sample1
                            ],
                        ),
                    ],
                ),
            },
        )

        # exec to register
        register_sv_model(sv_model=sv_model, stored_dir=Path("test"))

        # check if they are same or not
        expected_same_files = [
            "variance_model.onnx",
            "embedder_model.onnx",
            "decoder_model.onnx",
        ]
        match, mismatch, errors = filecmp.cmpfiles(
            f"./test/model/{sv_model_uuid}",
            f"./test/testdata/model/{sv_model_uuid}",
            expected_same_files,
        )
        self.assertListEqual(match, expected_same_files)
        self.assertListEqual(mismatch, [])
        self.assertListEqual(errors, [])

        # check if only the file size is more than 0,
        # because it's めんどい
        self.assertTrue(os.path.getsize(f"./test/model/{sv_model_uuid}/metas.json") > 0)

        expected_same_files = [
            "policy.md",
            "portrait.png",
            "icons/0.png",
            "voice_samples/0_001.wav",
        ]
        match, mismatch, errors = filecmp.cmpfiles(
            f"./test/speaker_info/{speaker_uuid}",
            f"./test/testdata/speaker_info/{speaker_uuid}",
            expected_same_files,
        )
        self.assertListEqual(match, expected_same_files)
        self.assertListEqual(mismatch, [])
        self.assertListEqual(errors, [])

        with open("./test/model/libraries.json", "r") as f:
            libraries = json.load(f)
            self.assertIn("official", libraries.keys())
            self.assertIn(sv_model_uuid, libraries.keys())
