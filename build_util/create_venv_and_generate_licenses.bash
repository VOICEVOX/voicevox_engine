# 仮想環境を作ってrequirements.txtをインストールし、ライセンス一覧を生成する

set -eux

if [ ! -v OUTPUT_LICENSE_JSON_PATH ]; then
    echo "OUTPUT_LICENSE_JSON_PATHが未定義です"
    exit 1
fi

VENV_PATH="licenses_venv"

python -m venv $VENV_PATH
source $VENV_PATH/bin/activate

pip install -r requirements-license.txt
python generate_licenses.py >$OUTPUT_LICENSE_JSON_PATH

deactivate

rm -rf $VENV_PATH
