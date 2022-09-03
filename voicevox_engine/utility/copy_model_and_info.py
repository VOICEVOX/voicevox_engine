import os
from pathlib import Path
import shutil
import json
import glob
from typing import Dict

from appdirs import user_data_dir

user_dir = Path(user_data_dir("sharevox-engine"))
model_dir = user_dir / "model"
libraries_json_path = model_dir / "libraries.json"
speaker_info_dir = user_dir / "speaker_info"


def copy_model_and_info(root_dir: Path):
    """
    engine_rootからuser_dirにモデルデータ・話者情報をコピーする
    """
    root_model_dir = root_dir / "model"
    root_speaker_info_dir = root_dir / "speaker_info"

    # モデルディレクトリが存在しなければすべてコピー
    if not model_dir.is_dir():
        shutil.copytree(root_model_dir, model_dir)
    else:
        # モデルディレクトリが存在する場合、libraries.jsonを参照しながらモデルの追加があるか確認する
        with open(root_model_dir / "libraries.json") as f:
            root_libraries: Dict[str, bool] = json.load(f)
        with open(libraries_json_path) as f:
            installed_libraries: Dict[str, bool] = json.load(f)
        for uuid in root_libraries.keys():
            value = installed_libraries.get(uuid)
            if value is None:
                installed_libraries[uuid] = True
                shutil.copytree(root_model_dir / uuid, model_dir / uuid)
        with open(libraries_json_path, "w") as f:
            json.dump(installed_libraries, f)

    # 話者情報ディレクトリが存在しなければすべてコピー
    if not speaker_info_dir.is_dir():
        shutil.copytree(root_speaker_info_dir, speaker_info_dir)
    else:
        # 話者情報ディレクトリが存在する場合、話者情報の追加があるか確認する
        speaker_infos = glob.glob(str(root_speaker_info_dir / "**"))
        for uuid in [os.path.basename(info) for info in speaker_infos]:
            speaker_dir = speaker_info_dir / uuid
            if not speaker_dir.is_dir():
                shutil.copytree(root_speaker_info_dir / uuid, speaker_dir)
            else:
                icons = glob.glob(str(root_speaker_info_dir / uuid / "icons" / "*"))
                for icon_name in [os.path.basename(icon) for icon in icons]:
                    icon_path = speaker_dir / "icons" / icon_name
                    if not icon_path.is_file():
                        shutil.copy2(root_speaker_info_dir / uuid / "icons" / icon_name, icon_path)
                voice_samples = glob.glob(str(root_speaker_info_dir / uuid / "voice_samples" / "*"))
                for voice_sample_name in [os.path.basename(voice_sample) for voice_sample in voice_samples]:
                    voice_sample_path = speaker_dir / "voice_samples" / voice_sample_name
                    if not voice_sample_path.is_file():
                        shutil.copy2(root_speaker_info_dir / uuid / "voice_samples" / voice_sample_name, voice_sample_path)
