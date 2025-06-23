import datetime

from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    func,
    select,
    text,
)

from .entities import Conversation, Speaker, Utterance

from ..config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
)


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
