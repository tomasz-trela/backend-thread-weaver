from pydantic import BaseModel
from typing import Optional


class UtteranceDTO(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str
    speaker_id: Optional[int]
    conversation_id: int
    speaker: Optional[str]

    class Config:
        orm_mode = True
