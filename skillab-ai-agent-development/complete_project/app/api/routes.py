"""API routes for chat endpoints."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.chat import ChatSession
from app.llm import get_llm

from .schemas import (
    AgentMetrics,
    CacheMetrics,
    ChatRequest,
    ChatResponseModel,
    ChatSettings,
    ConfigResponse,
    GuardrailsMetrics,
    HealthResponse,
    LLMMetrics,
    MemoryMetrics,
    MetricsResponse,
    ProviderConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Session cache for persistence
_sessions: dict[str, ChatSession] = {}


def get_or_create_session(
    session_id: str | None = None,
    settings: ChatSettings | None = None,
) -> ChatSession:
    """Get existing session or create new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    # Use settings if provided, otherwise defaults
    memory_enabled = settings.memory_enabled if settings else True
    persist_memory = settings.persist_memory if settings else bool(session_id)
    use_guardrails = settings.use_guardrails if settings else True
    llm_caching_enabled = settings.llm_caching_enabled if settings else False
    llm_caching_context = settings.llm_caching_context if settings else ""

    # Generate session_id for memory sessions (even if not persisting to DB)
    if memory_enabled and not session_id:
        import uuid
        session_id = uuid.uuid4().hex
        logger.info(f"[SESSION] Created new session: {session_id[:8]}...")

    # Log caching settings
    if llm_caching_enabled:
        context_len = len(llm_caching_context)
        estimated_tokens = context_len // 4
        logger.info(f"[CACHE] LLM caching enabled: context={context_len} chars (~{estimated_tokens} tokens)")

    # Create LLM with settings
    llm = None
    if settings:
        try:
            llm = get_llm(
                provider=settings.llm_provider,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
            )
        except ValueError as e:
            logger.warning(f"Failed to create LLM with settings: {e}, using default")
            llm = None

    session = ChatSession(
        llm=llm,
        memory_enabled=memory_enabled,
        persist_memory=persist_memory,
        session_id=session_id,
        use_guardrails=use_guardrails,
        llm_caching_enabled=llm_caching_enabled,
        llm_caching_context=llm_caching_context,
    )

    # Cache session for memory (both in-memory and persist)
    if session.session_id and memory_enabled:
        _sessions[session.session_id] = session

    return session


# Available LLM providers and their models
PROVIDER_CONFIGS = [
    ProviderConfig(
        name="ollama",
        models=["llama3.2", "llama3.1", "mistral", "mixtral", "codellama", "phi3"],
        default_model="llama3.2",
    ),
    ProviderConfig(
        name="anthropic",
        models=[
            "claude-sonnet-5",
            "claude-opus-4-8",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
        ],
        default_model="claude-sonnet-4-5",
    ),
    ProviderConfig(
        name="google",
        models=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3.5-flash",
            "gemini-2.5-flash-lite",
        ],
        default_model="gemini-2.5-flash",
    ),
]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get available configuration options and defaults."""
    return ConfigResponse(
        providers=PROVIDER_CONFIGS,
        defaults=ChatSettings(),
    )


@router.post("/chat", response_model=ChatResponseModel)
async def chat(request: ChatRequest):
    """
    Process a chat message and return response with metrics.

    Args:
        request: ChatRequest with message, optional session_id and intent

    Returns:
        ChatResponseModel with answer, metrics and session info
    """
    try:
        session = get_or_create_session(request.session_id, request.settings)

        # Determine intent from settings or request
        intent = request.intent
        if intent is None and request.settings and request.settings.intent != "auto":
            intent = request.settings.intent

        # Run blocking LLM call in thread pool to avoid event loop conflict
        response = await asyncio.to_thread(
            session.ask,
            question=request.message,
            intent=intent,
        )

        # Convert internal metrics to API schema
        chat_metrics = response.metrics
        metrics_dict = chat_metrics.to_dict()

        metrics = MetricsResponse(
            llm=LLMMetrics(**metrics_dict["llm"]),
            guardrails=GuardrailsMetrics(**metrics_dict["guardrails"]),
            cache=CacheMetrics(**metrics_dict["cache"]),
            memory=MemoryMetrics(**metrics_dict["memory"]),
            agent=AgentMetrics(**metrics_dict["agent"]),
        )

        return ChatResponseModel(
            answer=response.answer,
            session_id=session.session_id,
            intent=response.intent,
            status=response.status,
            metrics=metrics,
        )

    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session."""
    if session_id in _sessions:
        session = _sessions[session_id]
        deleted = session.clear_history()
        del _sessions[session_id]
        return {"deleted": deleted, "session_id": session_id}

    raise HTTPException(status_code=404, detail="Session not found")
