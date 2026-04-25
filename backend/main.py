import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine
from backend.routers import jobs, results, stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Formulation Wiki", lifespan=lifespan)

app.include_router(jobs.router)
app.include_router(results.router)
app.include_router(stream.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve React SPA only when the frontend has been built (always true in Docker)
if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
