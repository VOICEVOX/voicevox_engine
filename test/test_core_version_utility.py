from unittest import TestCase

from voicevox_engine.utility import get_latest_core_version, parse_core_version


class TestCoreVersion(TestCase):
    def test_parse_core_version(self):
        parse_core_version("0.0.0")
        parse_core_version("0.1.0")
        parse_core_version("0.10.0")
        parse_core_version("0.10.0-preview.1")
        parse_core_version("0.14.0")
        parse_core_version("0.14.0-preview.1")
        parse_core_version("0.14.0-preview.10")

    def test_get_latest_core_version(self):
        self.assertEqual(
            get_latest_core_version(
                versions=[
                    "0.0.0",
                    "0.1.0",
                    "0.10.0",
                    "0.10.0-preview.1",
                    "0.14.0",
                    "0.14.0-preview.1",
                    "0.14.0-preview.10",
                ]
            ),
            "0.14.0",
        )

        self.assertEqual(
            get_latest_core_version(
                versions=[
                    "0.14.0",
                    "0.15.0-preview.1",
                ]
            ),
            "0.15.0-preview.1",
        )
