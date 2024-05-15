set -eux

if [ ! -v DOWNLOAD_RESOURCE_PATH ]; then
    echo "DOWNLOAD_RESOURCE_PATHが未定義です"
    exit 1
fi

rm -r speaker_info
cp -r "${DOWNLOAD_RESOURCE_PATH}/character_info" speaker_info

# キャラクター情報の前処理をする
python "${DOWNLOAD_RESOURCE_PATH}/scripts/clean_character_info.py" \
    --character_info_dir speaker_info/

# マニフェスト
jq -s '.[0] * .[1]' engine_manifest.json "${DOWNLOAD_RESOURCE_PATH}/engine/engine_manifest.json" \
    > engine_manifest.json.tmp
mv engine_manifest.json.tmp engine_manifest.json

python build_util/merge_update_infos.py \
    resources/engine_manifest_assets/update_infos.json \
    "${DOWNLOAD_RESOURCE_PATH}/engine/engine_manifest_assets/update_infos.json" \
    resources/engine_manifest_assets/update_infos.json

for f in "${DOWNLOAD_RESOURCE_PATH}"/engine/engine_manifest_assets/*; do
    if [ "$(basename "${f}")" != "update_infos.json" ]; then
        cp "${f}" ./resources/engine_manifest_assets/
    fi
done
