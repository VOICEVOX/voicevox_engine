set -eux

if [ ! -v DOWNLOAD_RESOURCE_PATH ]; then
    echo "DOWNLOAD_RESOURCE_PATHが未定義です"
    exit 1
fi

rm -r speaker_info
cp -r $DOWNLOAD_RESOURCE_PATH/character_info speaker_info

# キャラクター情報の前処理をする
python $DOWNLOAD_RESOURCE_PATH/scripts/clean_character_info.py \
    --character_info_dir speaker_info/

# マニフェスト
jq -s '.[0] * .[1]' engine_manifest.json $DOWNLOAD_RESOURCE_PATH/engine/engine_manifest.json \
    > engine_manifest.json.tmp
mv engine_manifest.json.tmp engine_manifest.json

python build_util/merge_update_infos.py \
    engine_manifest_assets/update_infos.json \
    $DOWNLOAD_RESOURCE_PATH/engine/engine_manifest_assets/update_infos.json \
    engine_manifest_assets/update_infos.json

for f in $(ls $DOWNLOAD_RESOURCE_PATH/engine/engine_manifest_assets/* | grep -v update_infos.json); do
    cp $f ./engine_manifest_assets/
done
