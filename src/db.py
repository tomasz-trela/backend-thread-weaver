import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlmodel import (
    Field,
    Relationship,
    Session,
    SQLModel,
    create_engine,
    func,
    select,
    text,
)

from .config import settings

engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
    echo=True,
)


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


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    with Session(engine) as session:
        session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()

    SQLModel.metadata.create_all(engine)


def similarity_search(
    query_embedding: list[float],
    limit: int,
    speaker_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    session: Session,
) -> list[Utterance]:
    stmt = (
        select(Utterance)
        .join(Speaker)
        .order_by(Utterance.embedding.cosine_distance(query_embedding))
    )

    if start_date is not None:
        stmt = stmt.where(Utterance.conversation.has(Conversation.date >= start_date))

    if end_date is not None:
        stmt = stmt.where(Utterance.conversation.has(Conversation.date <= end_date))

    if speaker_id is not None:
        stmt = stmt.where(Utterance.speaker_id == speaker_id)

    if limit is not None:
        stmt = stmt.limit(limit)

    results = session.exec(stmt).all()
    return results


def full_text_search(
    query: str,
    limit: int,
    language: str,
    speaker_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    session: Session,
) -> list[Utterance]:
    stmt = (
        select(
            Utterance,
            func.ts_rank(
                func.to_tsvector(language, Utterance.text),
                func.websearch_to_tsquery(language, query),
            ).label("rank"),
        )
        .where(
            func.to_tsvector(language, Utterance.text).op("@@@")(
                func.websearch_to_tsquery(language, query)
            )
        )
        .order_by(
            func.ts_rank(
                func.to_tsvector(language, Utterance.text),
                func.websearch_to_tsquery(language, query),
            ).desc()
        )
    )

    if start_date is not None:
        stmt = stmt.where(Utterance.conversation.has(Conversation.date >= start_date))

    if end_date is not None:
        stmt = stmt.where(Utterance.conversation.has(Conversation.date <= end_date))

    if speaker_id is not None:
        stmt = stmt.where(Utterance.speaker_id == speaker_id)

    if limit is not None:
        stmt = stmt.limit(limit)

    utterances = []
    for utterance, rank in session.exec(stmt).all():
        utterances.append(utterance)

    return utterances
