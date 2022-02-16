# ビルド結果をテストする
import time
from subprocess import Popen

process = Popen(["./run"])

time.sleep(30)  # 待機
