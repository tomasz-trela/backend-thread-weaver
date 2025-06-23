import datetime
from typing import Any
from pgvector.sqlalchemy import Vector
from sqlmodel import Field, Relationship, SQLModel


class Speaker(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field()
    surname: str = Field()

    utterances: list["Utterance"] = Relationship(back_populates="speaker")


class Conversation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field()
    description: str = Field(default=None, nullable=True)
    created_at: datetime.datetime = Field(
        default=datetime.datetime.now(datetime.timezone.utc), nullable=True
    )
    youtube_id: str | None = Field(default=None, nullable=True)
    video_filename: str | None = Field(default=None, nullable=True)
    conversation_date: datetime.date | None = Field(default=None, nullable=True)

    utterances: list["Utterance"] = Relationship(back_populates="conversation")


class Utterance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    start_time: float = Field()
    end_time: float = Field()
    text: str = Field()
    embedding: Any = Field(sa_type=Vector(3072))

    speaker_id: int | None = Field(default=None, foreign_key="speaker.id")
    speaker: Speaker | None = Relationship(back_populates="utterances")

    conversation_id: int = Field(foreign_key="conversation.id")
    conversation: Conversation = Relationship(back_populates="utterances")
