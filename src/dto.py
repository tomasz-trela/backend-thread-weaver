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


class ProcessRequest(BaseModel):
    conversation_id: int
    filename: str
    segment: int
    speakers: list[int]


class ConversationRequest(BaseModel):
    name: str
    speakers: list[int]
    description: Optional[str] = None
    youtube_id: Optional[str] = None

    class Config:
        orm_mode = True
