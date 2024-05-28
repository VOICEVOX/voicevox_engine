from pydantic import BaseModel, Field


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(title="指定した話者に対してモーフィングの可否")
    # FIXME: add reason property
    # reason: str | None = Field(title="is_morphableがfalseである場合、その理由")
