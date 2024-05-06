set -eux

# リソースディレクトリのパスを検証する
if [ ! -v DOWNLOAD_RESOURCE_PATH ]; then
    echo "DOWNLOAD_RESOURCE_PATHが未定義です"
    exit 1
fi

# ダミーのキャラクター情報を製品版のキャラクター情報で置き換える
rm -r speaker_info
cp -r "${DOWNLOAD_RESOURCE_PATH}/character_info" speaker_info

# キャラクター情報を前処理する
python "${DOWNLOAD_RESOURCE_PATH}/scripts/clean_character_info.py" \
    --character_info_dir speaker_info/

# エンジンマニフェストに含まれるダミーの情報を製品版の情報で上書きする
jq -s '.[0] * .[1]' engine_manifest.json "${DOWNLOAD_RESOURCE_PATH}/engine/engine_manifest.json" \
    > engine_manifest.json.tmp
mv engine_manifest.json.tmp engine_manifest.json

# アップデート情報を整形する。TODO: `merge_update_info.py` のファイル名変更
python build_util/merge_update_infos.py engine_manifest_assets/update_infos.json

# エンジンのディレクトリへリソースのマニフェストアセットを複製する
for f in $(ls "${DOWNLOAD_RESOURCE_PATH}"/engine/engine_manifest_assets/* | grep -v update_infos.json); do
    cp "${f}" ./engine_manifest_assets/
done
