from unittest import TestCase
from unittest.mock import patch

from voicevox_engine.utility.core_utility import get_half_logical_cores


class TestHalfLogicalCores(TestCase):
    @patch("os.cpu_count", return_value=8)
    def test_half_logical_cores_even(self, mock_cpu_count):
        self.assertEqual(get_half_logical_cores(), 4)

    @patch("os.cpu_count", return_value=9)
    def test_half_logical_cores_odd(self, mock_cpu_count):
        self.assertEqual(get_half_logical_cores(), 4)

    @patch("os.cpu_count", return_value=None)
    def test_half_logical_cores_none(self, mock_cpu_count):
        self.assertEqual(get_half_logical_cores(), 0)
