import unittest

from fastapi.testclient import TestClient

from run import generate_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(generate_app(False))

    def tearDown(self):
        super().tearDown()

    def test_audio_query(self):
        """
        audio_queryのテスト
        """
        for i in range(0, 3):
            try:
                response = self.client.post(f"/audio_query?text=テスト用文字列&speaker={i}")
                self.assertEqual(response.status_code, 200)
            except AssertionError:
                # 対応してないspeaker idでちゃんとエラーを吐くか
                self.assertEqual(i, 2)
