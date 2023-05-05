import re
from unittest import TestCase


class TestRegexAquesTalk(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.regex_aquestalk = re.compile(r'^[\u30A1-\u30FA](?!.*([\'/_、？])\1+)[\u30A1-\u30FA_\'、/？].*$')

    def test_accept_aquestalk(self):
        self.assertIsNotNone(self.regex_aquestalk.fullmatch("コンニチワ？_コンバンワ"))
        self.assertIsNotNone(self.regex_aquestalk.fullmatch("コンニチワ'？、コンバンワ'？"))
        self.assertIsNotNone(self.regex_aquestalk.fullmatch("ワ'、ナ'ンデ_スカ？"))
        self.assertIsNotNone(self.regex_aquestalk.fullmatch("ワ'？"))
        self.assertIsNotNone(self.regex_aquestalk.fullmatch("コ'レワ/テ_スト'デ_ス"))

    def test_reject_aquestalk(self):
        self.assertIsNone(self.regex_aquestalk.fullmatch("ワ'、ナ'ンデ_スカ？？"))
        self.assertIsNone(self.regex_aquestalk.fullmatch("ワ'、、ナ'ンデ_スカ？"))
