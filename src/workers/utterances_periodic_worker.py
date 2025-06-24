from threading import Event

from sqlmodel import Session, select

from src.data.entities import Utterance
from src.data.googleapi import get_embeddings


def periodic_worker(session: Session, stop_event: Event):
    # while not stop_event.is_set():
    #     stmt = select(Utterance).where(Utterance.embedding == None).limit(1)
    #     utterance = session.exec(stmt).first()
    #     if utterance:
    #         try:
    #             embeddings = get_embeddings(utterance).embeddings[0].values
    #             print(f"Got embeddings for utterance {utterance.id}: {embeddings}")
    #             utterance.embedding = embeddings
    #             session.add(utterance)
    #             session.commit()
    #             stop_event.wait(timeout=10)
    #         except Exception as e:
    #             stop_event.wait(timeout=60)
    #     else:
    #         stop_event.wait(timeout=60)
    pass
