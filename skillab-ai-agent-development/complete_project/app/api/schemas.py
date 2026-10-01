"""Pydantic schemas for API request/response models."""
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Settings Schemas
# =============================================================================


class ChatSettings(BaseModel):
    """Chat settings that can be overridden per request."""

    # Tier 1 - Core Settings
    llm_provider: Literal["ollama", "anthropic", "google"] = "ollama"
    llm_model: str | None = None  # If None, use default for provider
    llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    use_guardrails: bool = True
    memory_enabled: bool = True  # In-session conversation memory
    persist_memory: bool = False  # Save to DB for cross-session persistence
    intent: Literal["auto", "rag", "sql", "chat"] = "auto"

    # Tier 2 - Advanced Settings
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_iterations: int = Field(default=3, ge=1, le=10)
    max_retries: int = Field(default=2, ge=0, le=5)
    use_llm_injection: bool = True

    # Tier 3 - Cache & Memory
    cache_enabled: bool = True
    cache_ttl_hours: int = Field(default=1, ge=1, le=24)

    # LLM Caching (Anthropic prompt caching)
    llm_caching_enabled: bool = False
    llm_caching_context: str = ""


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    models: list[str]
    default_model: str


class ConfigResponse(BaseModel):
    """Configuration response with available options."""

    providers: list[ProviderConfig]
    defaults: ChatSettings


class LLMMetrics(BaseModel):
    """LLM usage metrics."""

    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    latency_ms: int = 0
    calls_count: int = 0


class GuardrailsMetrics(BaseModel):
    """Guardrails check metrics."""

    checked: bool = False
    safe: bool = True
    blocked_category: str | None = None


class CacheMetrics(BaseModel):
    """Cache metrics."""

    semantic_hit: bool = False
    prompt_cache_hit: bool = False


class MemoryMetrics(BaseModel):
    """Memory metrics."""

    messages_count: int = 0
    session_id: str | None = None


class AgentMetrics(BaseModel):
    """Agent execution metrics."""

    type: str | None = None
    iterations: int = 0
    sql_query: str | None = None
    retry_count: int = 0
    steps_count: int = 0


class MetricsResponse(BaseModel):
    """Complete metrics response."""

    llm: LLMMetrics = Field(default_factory=LLMMetrics)
    guardrails: GuardrailsMetrics = Field(default_factory=GuardrailsMetrics)
    cache: CacheMetrics = Field(default_factory=CacheMetrics)
    memory: MemoryMetrics = Field(default_factory=MemoryMetrics)
    agent: AgentMetrics = Field(default_factory=AgentMetrics)


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = None
    intent: Literal["rag", "sql", "chat"] | None = None
    settings: ChatSettings | None = None  # Optional settings override


class ChatResponseModel(BaseModel):
    """Chat response payload."""

    answer: str
    session_id: str | None = None
    intent: Literal["rag", "sql", "chat"]
    status: Literal["success", "partial", "failed", "blocked"]
    metrics: MetricsResponse = Field(default_factory=MetricsResponse)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
