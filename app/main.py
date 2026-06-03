from functools import lru_cache
import sys

from fastapi import FastAPI
from pydantic import BaseModel
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from app.agent import SalesAgent
from app.api.middlewares import LoggingMiddleware
from app.config import settings


def setup_logging():
    logger.remove()
    # JSON-serialized log file for Loki/Promtail
    logger.add(
        "/app/logs/api.log",
        rotation="10 MB",
        retention="5 days",
        serialize=True,
        level="INFO",
    )
    # Pretty stdout for terminal / docker console logs
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )


setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(LoggingMiddleware)
Instrumentator(excluded_handlers=["/metrics", "/health"]).instrument(app).expose(app)


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
