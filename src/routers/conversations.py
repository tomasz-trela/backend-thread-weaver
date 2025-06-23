from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile, BackgroundTasks

from sqlmodel import delete, select

from ..helpers import (
    create_conversation_from_audio,
    create_conversation_from_text,
    run_async_task,
)

from ..models.dto import ConversationUpdateRequest, UtteranceDTO
from ..data.googleapi import get_embeddings

from ..data.db import (
    Conversation,
    Speaker,
    Utterance,
    full_text_search,
    similarity_search,
)
from ..typedefs import SessionDep
from ..services.transcription import TranscriptionService

router = APIRouter(prefix="/conversations", tags=["Conversations"])

transcriptionService = TranscriptionService()


# @router.post("/yt", status_code=201)
@router.post("/audio", status_code=201)
async def add_audio_converstaion_to_tasks(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile,
    name: str = Form(...),
    speakers: List[int] = Form(...),
    description: Optional[str] = Form(None),
    youtube_id: Optional[str] = Form(None),
    conversation_date: Optional[date] = Form(None),
):
    background_tasks.add_task(
        run_async_task,
        create_conversation_from_audio,
        session,
        audio_file,
        name,
        speakers,
        transcriptionService,
        description,
        youtube_id,
        conversation_date,
    )
    return {"message": "Conversation creation task has been started"}


@router.post("/text", status_code=201)
async def add_text_converstaion_to_tasks(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    speaker_file: UploadFile,
    whisper_file: UploadFile,
    name: str = Form(...),
    speakers: List[int] = Form(...),
    description: Optional[str] = Form(None),
    youtube_id: Optional[str] = Form(None),
    conversation_date: Optional[date] = Form(None),
):
    speaker_data_bytes = await speaker_file.read()
    whisper_data_bytes = await whisper_file.read()

    background_tasks.add_task(
        run_async_task,
        create_conversation_from_text,
        session,
        speaker_data_bytes,
        whisper_data_bytes,
        name,
        speakers,
        description,
        youtube_id,
        conversation_date,
    )
    return {"message": "Conversation creation task has been started"}


@router.put("/{id}")
async def update_conversation(
    id: int,
    data: ConversationUpdateRequest,
    session: SessionDep,
) -> Conversation:
    conversation = session.get(Conversation, id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    for key, value in data.model_dump().items():
        if value is not None:
            setattr(conversation, key, value)

    session.commit()
    session.refresh(conversation)
    return conversation


@router.delete("/{id}", status_code=204)
async def delete_conversation(id: int, session: SessionDep):
    conversation_to_delete = session.get(Conversation, id)

    if not conversation_to_delete:
        raise HTTPException(status_code=404, detail="Conversation not found")

    utterance_delete_stmt = delete(Utterance).where(Utterance.id == id)
    session.exec(utterance_delete_stmt)

    session.delete(conversation_to_delete)
    session.commit()


@router.get("/similarity-search", response_model=list[UtteranceDTO])
async def get_similarity_search(
    query: str,
    session: SessionDep,
    limit: Optional[int] = None,
    speaker_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    query_embedding = get_embeddings([query]).embeddings[0].values
    results = similarity_search(
        query_embedding, limit, speaker_id, start_date, end_date, session
    )

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            conversation=u.conversation,
            speaker=u.speaker,
            speaker_surname=u.speaker.surname if u.speaker else None,
        )
        for u in results
    ]


@router.get("/full-text", response_model=list[UtteranceDTO])
async def get_full_text(
    query: str,
    session: SessionDep,
    limit: Optional[int] = 20,
    language: Optional[str] = "simple",
    speaker_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    results = full_text_search(
        query, limit, language, speaker_id, start_date, end_date, session
    )

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            conversation=u.conversation,
            speaker=u.speaker,
            speaker_surname=u.speaker.surname if u.speaker else None,
        )
        for u in results
    ]


@router.get("/{conversation_id}/speakers")
async def get_speakers(conversation_id: int, session: SessionDep) -> Any:
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        return {"error": "Conversation not found"}

    speakers = session.exec(
        select(Speaker).where(
            Speaker.id.in_(
                select(Utterance.speaker_id)
                .where(Utterance.speaker_id != None)
                .where(Utterance.conversation_id == conversation.id)
                .distinct()
            )
        )
    ).all()

    return speakers


@router.get("/hybrid-search", response_model=list[UtteranceDTO])
async def get_hybrid_search(
    query: str,
    session: SessionDep,
    limit: Optional[int] = 20,
    speaker_id: Optional[int] = None,
    language: Optional[str] = "simple",
    rrf_k: int = 60,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Use a low rrf_k when:
        - You have very high confidence in your individual searchers.
        - You believe the #1 result from either vector or FTS is highly likely to be the best answer.
        - You want an "aggressive" fusion that prioritizes the top-ranked items above all else.
    Performs a hybrid search by combining full-text and similarity search results
    using Reciprocal Rank Fusion (RRF).

    Use a high rrf_k when:
        - You want to balance the influence of both keyword and semantic search.
        - You believe that documents relevant to both search methods are more valuable than documents that are only relevant to one.
        - You want a more stable and robust ranking that is less sensitive to small changes in the top ranks of individual searchers. This is why it's a good default.

    Basic rrf_k values:
        - 60: Good default value, balances both search methods.
        - 30: More aggressive, prioritizes top results from either method.
        - 10: Very aggressive, only considers the top results from either method.
        - 100: More conservative, gives more weight to lower-ranked results.
        - 1000: Extremely conservative, considers a very wide range of results.
    """
    fetch_limit = limit * 2 if limit else 40

    fts_results = full_text_search(
        query, fetch_limit, language, speaker_id, start_date, end_date, session
    )

    query_embedding = get_embeddings([query]).embeddings[0].values
    sim_results = similarity_search(
        query_embedding, fetch_limit, speaker_id, start_date, end_date, session
    )
    fused_scores = {}
    results_map = {}

    for rank, utterance in enumerate(fts_results):
        results_map[utterance.id] = utterance
        fused_scores[utterance.id] = fused_scores.get(utterance.id, 0) + 1 / (
            rrf_k + rank
        )

    for rank, utterance in enumerate(sim_results):
        results_map[utterance.id] = utterance
        fused_scores[utterance.id] = fused_scores.get(utterance.id, 0) + 1 / (
            rrf_k + rank
        )

    sorted_ids = sorted(
        fused_scores.keys(), key=lambda id: fused_scores[id], reverse=True
    )

    final_results = [results_map[id] for id in sorted_ids]

    final_limited_results = final_results[:limit] if limit else final_results

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            conversation=u.conversation,
            speaker=u.speaker,
            speaker_surname=u.speaker.surname if u.speaker else None,
        )
        for u in final_limited_results
    ]


@router.get("/{conversation_id}/utterances", response_model=list[UtteranceDTO])
async def get_utterances(
    conversation_id: int,
    session: SessionDep,
) -> list[UtteranceDTO]:
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    utterances = session.exec(
        select(Utterance)
        .where(Utterance.conversation_id == conversation.id)
        .order_by(Utterance.start_time)
    ).all()

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            conversation=u.conversation,
            speaker=u.speaker,
            speaker_surname=u.speaker.surname if u.speaker else None,
        )
        for u in utterances
    ]
