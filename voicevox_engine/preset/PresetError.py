"""プリセットに関するエラー"""


class PresetInputError(Exception):
    """クライアントのリクエスト値に起因するエラー"""
    pass

class PresetInternalError(Exception):
    """サーバー/ENGINE に起因するエラー"""
    pass
