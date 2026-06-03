from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import SalesAgent
from app.api.middlewares import LoggingMiddleware
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(LoggingMiddleware)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str


@lru_cache(maxsize=1)
def get_agent() -> SalesAgent:
    return SalesAgent()


@app.post(f"{settings.API_V1_STR}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    response = await get_agent().chat(request.session_id, request.message)
    return ChatResponse(session_id=request.session_id, response=response)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
