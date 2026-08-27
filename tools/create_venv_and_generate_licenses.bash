# 仮想環境を作って実行に必要な依存のみをインストールし、ライセンス一覧を生成する

set -eux

if [ ! -v OUTPUT_LICENSE_JSON_PATH ]; then
    echo "OUTPUT_LICENSE_JSON_PATHが未定義です"
    exit 1
fi

uv venv "licenses_venv"
export VIRTUAL_ENV="licenses_venv"
uv sync --active --group licenses
uv run --active tools/generate_licenses.py > "${OUTPUT_LICENSE_JSON_PATH}"

rm -rf $VIRTUAL_ENV
unset VIRTUAL_ENV
