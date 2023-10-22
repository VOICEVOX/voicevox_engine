#!/usr/bin/env bash
# !!! コードサイニング証明書を取り扱うので取り扱い注意 !!!

# eSignerCKAを使ってコード署名する

set -eu

if [ ! -v ESIGNERCKA_USERNAME ]; then # eSignerCKAのユーザー名
    echo "ESIGNERCKA_USERNAMEが未定義です"
    exit 1
fi
if [ ! -v ESIGNERCKA_PASSWORD ]; then # eSignerCKAのパスワード
    echo "ESIGNERCKA_PASSWORDが未定義です"
    exit 1
fi
if [ ! -v ESIGNERCKA_TOTP_SECRET ]; then # eSignerCKAのTOTP Secret
    echo "ESIGNERCKA_TOTP_SECRETが未定義です"
    exit 1
fi

if [ $# -ne 1 ]; then
    echo "引数の数が一致しません"
    exit 1
fi
target_file_glob="$1"

# eSignerCKAのセットアップ
INSTALL_DIR='..\eSignerCKA'
if [ ! -d "$INSTALL_DIR" ]; then
    curl -LO "https://github.com/SSLcom/eSignerCKA/releases/download/v1.0.6/SSL.COM-eSigner-CKA_1.0.6.zip"
    unzip -o SSL.COM-eSigner-CKA_1.0.6.zip
    mv ./*eSigner*CKA_*.exe eSigner_CKA_Installer.exe
    powershell "
        & ./eSigner_CKA_Installer.exe /CURRENTUSER /VERYSILENT /SUPPRESSMSGBOXES /DIR='$INSTALL_DIR' | Out-Null
        & '$INSTALL_DIR\eSignerCKATool.exe' config -mode product -user '$ESIGNERCKA_USERNAME' -pass '$ESIGNERCKA_PASSWORD' -totp '$ESIGNERCKA_TOTP_SECRET' -key '$INSTALL_DIR\master.key' -r
        & '$INSTALL_DIR\eSignerCKATool.exe' unload
    "
    rm SSL.COM-eSigner-CKA_1.0.6.zip eSigner_CKA_Installer.exe
fi

# 証明書を読み込む
powershell "& '$INSTALL_DIR\eSignerCKATool.exe' load"

# shellcheck disable=SC2016
THUMBPRINT=$(
    powershell '
        $CodeSigningCert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Select-Object -First 1
        echo "$($CodeSigningCert.Thumbprint)"
    '
)

# 指定ファイルに署名する
function codesign() {
    TARGET="$1"
    # shellcheck disable=SC2012
    SIGNTOOL=$(ls "C:/Program Files (x86)/Windows Kits/"10/bin/*/x86/signtool.exe | sort -V | tail -n 1) # なぜかこれじゃないと動かない
    powershell "& '$SIGNTOOL' sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /sha1 '$THUMBPRINT' '$TARGET'"
}

# 指定ファイルが署名されているか
function is_signed() {
    TARGET="$1"
    SIGNTOOL=$(find "C:/Program Files (x86)/Windows Kits/10/App Certification Kit" -name "signtool.exe" | sort -V | tail -n 1)
    powershell "& '$SIGNTOOL' verify /pa '$TARGET'" >/dev/null 2>&1 || return 1
}

# 署名されていなければ署名
# shellcheck disable=SC2012,SC2086
ls $target_file_glob | while read -r target_file; do
    if is_signed "$target_file"; then
        echo "署名済み: $target_file"
    else
        echo "署名開始: $target_file"
        codesign "$target_file"
    fi
done

# 証明書を破棄
powershell "& '$INSTALL_DIR\eSignerCKATool.exe' unload"
