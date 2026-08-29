#!/usr/bin/env bash
# !!! コードサイニング証明書を取り扱うので取り扱い注意 !!!

# 一時キーチェーンを破棄し、署名用Identityを削除する

set -eu

if [ ! -v CODESIGN_IDENTITY_PATH ]; then # 署名用Identityの出力先
    echo "CODESIGN_IDENTITY_PATHが未定義です"
    exit 1
fi
if [ ! -v KEYCHAIN_PATH_PATH ]; then # 一時キーチェーンのパスの出力先
    echo "KEYCHAIN_PATH_PATHが未定義です"
    exit 1
fi

KEYCHAIN_PATH="$(<"$KEYCHAIN_PATH_PATH")"

# キーチェーンを削除
security delete-keychain "$KEYCHAIN_PATH"

# 出力ファイルを削除
rm "$CODESIGN_IDENTITY_PATH"
rm "$KEYCHAIN_PATH_PATH"
