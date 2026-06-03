from functools import lru_cache
import sys

import httpx
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


async def check_ollama_ready() -> bool:
    """Check if Ollama is ready by verifying the model is available."""
    if settings.LLM_PROVIDER != "ollama":
        return True
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags"
            )
            if response.status_code == 200:
                tags = response.json().get("models", [])
                model_names = [m.get("name", "") for m in tags]
                if any(settings.OLLAMA_MODEL in name for name in model_names):
                    logger.info(f"Ollama model {settings.OLLAMA_MODEL} is ready")
                    return True
    except Exception as e:
        logger.warning(f"Ollama not ready yet: {e}")
    
    return False


@app.on_event("startup")
async def startup_event():
    """Verify LLM provider is ready on startup."""
    if settings.LLM_PROVIDER == "ollama":
        logger.info("Waiting for Ollama to be ready...")
        max_retries = 60
        for attempt in range(max_retries):
            if await check_ollama_ready():
                logger.info("Ollama is ready!")
                break
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Ollama not ready yet, retrying in 2s...")
            await __import__("asyncio").sleep(2)
        else:
            logger.warning("Ollama was not ready after 2 minutes. Proceeding anyway...")


@app.post(f"{settings.API_V1_STR}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    response = await get_agent().chat(request.session_id, request.message)
    return ChatResponse(session_id=request.session_id, response=response)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
