from unittest import TestCase

from voicevox_engine.utility.core_version import parse_core_version, get_latest_core_version


class TestCoreVersion(TestCase):
    def test_parse_core_version(self):
        parse_core_version("0.1.0")
        parse_core_version("0.10.preview.1")
        parse_core_version("0.10.0")
        parse_core_version("0.14.0")
        parse_core_version("0.14.0.preview.1")
        parse_core_version("0.14.0.preview.10")

    def test_get_latest_core_version(self):
        self.assertEqual(
            get_latest_core_version(versions=[
                "0.1.0",
                "0.10.preview.1",
                "0.10.0",
                "0.14.0",
                "0.14.0.preview.1",
                "0.14.0.preview.10",
            ]),
            "0.14.0",
        )
