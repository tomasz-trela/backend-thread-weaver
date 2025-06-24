from pydantic import BaseModel
from typing import Optional
from datetime import date
from src.data.db import Conversation, Speaker
from src.data.entities import ConversationStatus


class UtteranceDTO(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str
    conversation_id: int
    conversation: Conversation
    speaker_id: Optional[int] = None
    speaker_surname: Optional[str] = None
    speaker: Optional[Speaker] = None


class UtteranceUpdateRequest(BaseModel):
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: Optional[str] = None
    speaker_id: Optional[int] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    youtube_id: Optional[str] = None
    video_filename: Optional[str] = None
    conversation_date: Optional[date] = None
    youtube_url: Optional[str] = None
    status: Optional[ConversationStatus] = None


class ConversationCreateRequest(BaseModel):
    title: str
    description: str
    youtube_id: Optional[str] = None
    video_filename: Optional[str] = None
    conversation_date: Optional[date] = None
    youtube_url: Optional[str] = None


class SpeakerUpdateRequest(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None


class SpeakerCreateRequest(BaseModel):
    name: str
    surname: str
