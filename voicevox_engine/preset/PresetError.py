"""プリセットに関するエラー"""


class PresetInputError(Exception):
    """受け入れ不可能な入力値に起因するエラー"""

    pass


class PresetInternalError(Exception):
    """サーバー/ENGINE に起因するエラー"""

    pass
