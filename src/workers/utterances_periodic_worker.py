from threading import Event

from sqlmodel import Session, select

from src.data.entities import Utterance
from src.data.googleapi import get_embeddings
from src.data.db import get_raw_session

def periodic_worker(stop_event: Event):
    while not stop_event.is_set():
        session: Session = get_raw_session()
        
        stmt = select(Utterance).where(Utterance.embedding == None).limit(1)
        utterance = session.exec(stmt).first()
        if utterance:
            try:
                embeddings = get_embeddings(utterance).embeddings[0].values
                print(f"Got embeddings for utterance {utterance.id}: {embeddings}")
                utterance.embedding = embeddings
                session.add(utterance)
                session.commit()
                stop_event.wait(timeout=2)
            except Exception as e:
                stop_event.wait(timeout=60)
        else:
            stop_event.wait(timeout=60)

        session.close()