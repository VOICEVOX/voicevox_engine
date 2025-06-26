# メンテナンスガイドライン

このリポジトリは VOICEVOX OSS 用のコードを管理しています。  
GitHub Releases には製品版 VOICEVOX のビルド済みパッケージと VVPP パッケージが配置されています。  
Docker Hub の `voicevox/voicevox_engine` リポジトリに製品版 VOICEVOX エンジンの Docker イメージが配置されています。

## 新しいバージョンのリリース方法

ブランチ戦略やバージョンニングに関しては`VOICEVOX/voicevox_project`リポジトリの`docs/リリース戦略.md`を参照してください。

### 新しいマイナーバージョン(0.XX.0)のリリース

`VOICEVOX/voicevox_project` リポジトリの`docs/アップデート確認作業テンプレート.md`にタスクリストがあります。  
以下の順序で進めます。

1. アップデート情報を`resources/engine_manifest_assets/update_infos.json`に追加
2. スナップショットテストの更新
3. Github Workflow の `VOICEVOX_RESOURCE_VERSION`を更新
4. デフォルトブランチにプルリクエスト・マージ
5. パッケージ版・Docker 版を`.github/workflows/build-engine.yml`でビルド
6. Github Workflow の完了まで待機
7. エディタ(`VOICEVOX/voicevox`)があれば、エディタのリリース完了を待機
8. Releases の説明を編集
   - 今の最新の latest のリリースノートをコピーして書き換える
9. Releases の prerelease を外して latest にする
10. Docker Hub の latest を`.github/workflows/build-latest-engine-container.yml`で更新する
11. Releases を作成した commit から `release-0.XX` ブランチを作成して push する

### 新しいパッチバージョン(0.XX.Y)のリリース

`VOICEVOX/voicevox_project` リポジトリの`docs/hotfix確認作業テンプレート.md`にタスクリストがあります。  
以下の順序で進めます。

1. アップデート情報を`resources/engine_manifest_assets/update_infos.json`に追加
2. 新しいキャラクターがいる場合は辞書を更新
3. スナップショットテストの更新
4. Github Workflow の `VOICEVOX_RESOURCE_VERSION`と`VOICEVOX_CORE_VERSION`を更新
5. `release-0.XX` ブランチにプルリクエスト・マージ
6. `新しいマイナーバージョン(0.XX.0)のリリース`の手順 5 から手順 10 までを実行
