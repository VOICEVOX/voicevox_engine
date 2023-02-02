from unittest import TestCase
from voicevox_engine.utility import parse_core_version

class TestParseCoreVersion(TestCase):
    def test_parse_core_version(self):
      parse_core_version('0.1.0')
      parse_core_version('0.10.preview.1')
      parse_core_version('0.14.0')
      parse_core_version('0.14.0.preview.1')
      parse_core_version('0.14.0.preview.10')
