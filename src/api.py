from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .data.yt_dlp import get_yt_dlp

from .workers import conversations_periodic_worker, utterances_periodic_worker


from .data.db import (
    get_session,
    init_db,
)

from .routers import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    session_gen = get_session()
    session = next(session_gen)

    yt_dlp_gen = get_yt_dlp()
    yt_dlp = next(yt_dlp_gen)

    stop_event = threading.Event()

    conversations_worker_thread = threading.Thread(
        target=conversations_periodic_worker.periodic_worker,
        args=(session, yt_dlp, stop_event),
        daemon=True,
    )
    utterances_worker_thread = threading.Thread(
        target=utterances_periodic_worker.periodic_worker,
        args=(session, stop_event),
        daemon=True,
    )

    conversations_worker_thread.start()
    utterances_worker_thread.start()

    try:
        yield
    finally:
        stop_event.set()
        conversations_worker_thread.join()
        utterances_worker_thread.join()

        try:
            next(session_gen)
        except StopIteration:
            pass

        try:
            next(yt_dlp_gen)
        except StopIteration:
            pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}


app.include_router(api.router)
