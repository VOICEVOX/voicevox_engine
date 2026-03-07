#!/usr/bin/env bash
# !!! コードサイニング証明書を取り扱うので取り扱い注意 !!!

# 一時キーチェーンを破棄し、署名用Identityを削除する

set -eu

if [ ! -v CODESIGN_IDENTITY_PATH ]; then
    echo "CODESIGN_IDENTITY_PATHが未定義です"
    exit 1
fi
if [ ! -v KEYCHAIN_PATH_PATH ]; then
    echo "KEYCHAIN_PATH_PATHが未定義です"
    exit 1
fi

KEYCHAIN_PATH="$(head -n 1 "$KEYCHAIN_PATH_PATH")"

# キーチェーンリストから除外
security list-keychains -d user -s "$(security list-keychains -d user | tr -d '"' | grep -v "$KEYCHAIN_PATH" | xargs)"

# キーチェーンを削除
security delete-keychain "$KEYCHAIN_PATH"

# 出力ファイルを削除
rm "$CODESIGN_IDENTITY_PATH"
rm "$KEYCHAIN_PATH_PATH"
