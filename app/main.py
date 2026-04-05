import deepagents
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .deep_agent_runtime import run_chat

app = FastAPI(
    title="Project Nexus",
    description="FastAPI backend with deepagents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Request / response models
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


@app.post("/chat")
async def chat(request: ChatRequest):
    return await run_chat(
        message=request.message,
        thread_id=request.thread_id,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "deepagents": deepagents.__version__}

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Project Nexus API",
        "docs": "/docs",
        "deepagents_version": deepagents.__version__,
    }
