from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import (
    init_db,
)

from routers import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}


app.include_router(api.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
