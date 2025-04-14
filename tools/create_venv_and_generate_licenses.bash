# 仮想環境を作ってrequirements.txtをインストールし、ライセンス一覧を生成する

set -eux

if [ ! -v OUTPUT_LICENSE_JSON_PATH ]; then
    echo "OUTPUT_LICENSE_JSON_PATHが未定義です"
    exit 1
fi

VENV_PATH="licenses_venv"

uv venv $VENV_PATH
uv sync
# requirements-dev.txt でバージョン指定されている pip-licenses をインストールする
uv pip install "$(grep pip-licenses requirements-dev.txt | cut -f 1 -d ';')"
uv run tools/generate_licenses.py > "${OUTPUT_LICENSE_JSON_PATH}"

rm -rf $VENV_PATH
