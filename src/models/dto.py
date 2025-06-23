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
    speaker_id: Optional[int]
    conversation_id: int
    conversation: Conversation
    speaker_surname: Optional[str]
    speaker: Optional[Speaker]


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
    description: str = None
    youtube_id: Optional[str] = None
    video_filename: Optional[str] = None
    conversation_date: Optional[date] = None
    youtube_url: Optional[str] = None
    status: Optional[ConversationStatus] = None


class SpeakerUpdateRequest(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None


class SpeakerCreateRequest(BaseModel):
    name: str
    surname: str
