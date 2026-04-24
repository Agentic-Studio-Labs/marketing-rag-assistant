from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    auth,
    content,
    generated,
    integrations,
    jobs,
    me,
    settings,
    uploads,
)
from shared.config import settings as cloud_settings
from shared.db import close_pool, init_schema, managed_connection, open_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    with managed_connection() as conn:
        init_schema(conn)
    yield
    close_pool()


app = FastAPI(title="Content Intelligence Hub Cloud API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(content.router)
app.include_router(generated.router)
app.include_router(jobs.router)
app.include_router(settings.router)
app.include_router(integrations.router)
app.include_router(uploads.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "port": cloud_settings.port,
        "mode": "cloud",
    }
