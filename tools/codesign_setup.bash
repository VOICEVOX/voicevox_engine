#!/usr/bin/env bash
# !!! コードサイニング証明書を取り扱うので取り扱い注意 !!!

# .p12証明書を使って一時キーチェーンをセットアップし、署名用Identityを出力する

set -eu

if [ ! -v P12_PATH ]; then
    echo "P12_PATHが未定義です"
    exit 1
fi
if [ ! -v P12_PASSWORD ]; then
    echo "P12_PASSWORDが未定義です"
    exit 1
fi
if [ ! -v CODESIGN_IDENTITY_PATH ]; then
    echo "CODESIGN_IDENTITY_PATHが未定義です"
    exit 1
fi
if [ ! -v KEYCHAIN_PATH_PATH ]; then
    echo "KEYCHAIN_PATH_PATHが未定義です"
    exit 1
fi

# 一時キーチェーンのセットアップ
KEYCHAIN_PATH="$(mktemp -d)/codesign.keychain-db"
KEYCHAIN_PASSWORD="$(uuidgen)"
security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"

# Apple中間証明書のインポート
DEVELOPER_ID_G2_CA="$(mktemp)"
curl -fsSL -o "$DEVELOPER_ID_G2_CA" "https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer"
security import "$DEVELOPER_ID_G2_CA" -k "$KEYCHAIN_PATH"
rm "$DEVELOPER_ID_G2_CA"

# .p12証明書のインポート
security import "$P12_PATH" -k "$KEYCHAIN_PATH" -P "$P12_PASSWORD" -T /usr/bin/codesign -A
security set-key-partition-list -S apple-tool:,apple: -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH" >/dev/null
security list-keychains -d user -s "$KEYCHAIN_PATH" "$(security list-keychains -d user | tr -d '"' | xargs)"

# 署名用Identityの取得
IDENTITY=$(security find-identity -v -p codesigning "$KEYCHAIN_PATH" | awk 'match($0,/[0-9A-F]{40}/){print substr($0,RSTART,RLENGTH); exit}')
if [ -z "$IDENTITY" ]; then
    echo "署名用の有効なIdentityが見つかりません"
    exit 1
fi

# 署名用Identityを出力
echo "$IDENTITY" >"$CODESIGN_IDENTITY_PATH"

# キーチェーンパスを出力
echo "$KEYCHAIN_PATH" >"$KEYCHAIN_PATH_PATH"
