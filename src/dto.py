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


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    youtube_id: Optional[str] = None
    video_filename: Optional[str] = None


class SpeakerUpdateRequest(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None


class SpeakerCreateRequest(BaseModel):
    name: str
    surname: str
