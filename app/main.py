# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import init_db
from app.routers import users, lists


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AING Todo Demo", lifespan=lifespan)
app.include_router(users.router)
app.include_router(lists.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
