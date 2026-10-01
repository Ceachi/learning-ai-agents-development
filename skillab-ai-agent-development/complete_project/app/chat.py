"""
Chat Module - Q&A loop with conversation history.

Usage:
    from app.chat import ChatSession

    # In-memory (default)
    session = ChatSession()
    response = session.ask("Ce este o licitație deschisă?")

    # Cu persistență în DB
    session = ChatSession(persist_memory=True, session_id="user-123")
    response = session.ask("Câte achiziții au fost în 2024?")
"""
import logging
from dataclasses import dataclass, field

from app.agents import AnalystAgent, Orchestrator, Intent, route
from app.config import get_settings
from app.db.database import transaction
from app.guardrails import guard
from app.llm import LLMProvider, get_llm
from app.metrics import (
    AgentMetrics,
    CacheMetrics,
    ChatMetrics,
    GuardrailsMetrics,
    MemoryMetrics,
)
from app.optimize.memory import ConversationMemory
from app.prompts import PromptRegistry, get_prompts

logger = logging.getLogger(__name__)
_settings = get_settings()

# Default tables config pentru AnalystAgent
DEFAULT_TABLES_CONFIG = {
    "achizitii_directe": {"schema_path": "data/schemas/achizitii_directe.json"},
    "anunturi_initiere": {"schema_path": "data/schemas/anunturi_initiere.json"},
}


@dataclass(slots=True)
class ChatResponse:
    """Răspunsul sesiunii de chat."""
    answer: str
    intent: Intent
    status: str
    metrics: ChatMetrics = field(default_factory=ChatMetrics)


class ChatSession:
    """
    Sesiune de chat cu istoric și routing automat.

    Args:
        llm: Provider LLM (opțional, se auto-detectează)
        tables_config: Configurație tabele pentru AnalystAgent
        memory_enabled: Dacă True, ține minte conversația în sesiune
        persist_memory: Dacă True, istoricul e persistat în DB
        session_id: ID pentru persistență (generat automat dacă None)
        use_guardrails: Dacă True, verifică inputul înainte de procesare
        llm_caching_enabled: Dacă True, folosește prompt caching (Anthropic)
        llm_caching_context: Context sistem pentru prompt caching
    """

    __slots__ = (
        "llm",
        "tables_config",
        "_history",
        "_memory_enabled",
        "_persist",
        "_session_id",
        "_use_guardrails",
        "_llm_caching_enabled",
        "_llm_caching_context",
        "_orchestrator",
        "_analyst",
        "_prompts",
    )

    def __init__(
        self,
        llm: LLMProvider | None = None,
        tables_config: dict | None = None,
        memory_enabled: bool = True,
        persist_memory: bool = False,
        session_id: str | None = None,
        use_guardrails: bool = True,
        llm_caching_enabled: bool = False,
        llm_caching_context: str = "",
    ):
        self.llm = llm or get_llm()
        self.tables_config = tables_config or DEFAULT_TABLES_CONFIG
        self._history: list[dict[str, str]] = []
        self._memory_enabled = memory_enabled
        self._persist = persist_memory
        self._session_id = session_id
        self._use_guardrails = use_guardrails
        self._llm_caching_enabled = llm_caching_enabled
        self._llm_caching_context = llm_caching_context
        self._orchestrator: Orchestrator | None = None
        self._analyst: AnalystAgent | None = None
        self._prompts: PromptRegistry | None = None

    @property
    def orchestrator(self) -> Orchestrator:
        """Lazy init pentru Orchestrator (RAG)."""
        if self._orchestrator is None:
            self._orchestrator = Orchestrator(
                llm=self.llm,
                llm_caching_enabled=self._llm_caching_enabled,
                llm_caching_context=self._llm_caching_context,
            )
        return self._orchestrator

    @property
    def analyst(self) -> AnalystAgent:
        """Lazy init pentru AnalystAgent (SQL)."""
        if self._analyst is None:
            self._analyst = AnalystAgent(
                tables_config=self.tables_config,
                llm=self.llm,
                llm_caching_enabled=self._llm_caching_enabled,
                llm_caching_context=self._llm_caching_context,
            )
        return self._analyst

    @property
    def prompts(self) -> PromptRegistry:
        """Lazy init pentru prompts."""
        if self._prompts is None:
            self._prompts = get_prompts()
        return self._prompts

    @property
    def history(self) -> list[dict[str, str]]:
        """Returnează istoricul conversației."""
        if self._persist:
            with transaction() as session:
                memory = ConversationMemory(self._session_id, session)
                return memory.get_messages()
        return self._history

    @property
    def session_id(self) -> str | None:
        """ID-ul sesiunii (pentru memory sau persist)."""
        return self._session_id

    def ask(
        self,
        question: str,
        intent: Intent | None = None,
    ) -> ChatResponse:
        """
        Procesează o întrebare.

        Args:
            question: Întrebarea utilizatorului
            intent: Intent explicit (None = auto-detect via classifier)

        Returns:
            ChatResponse cu answer, intent, status și metrics
        """
        logger.info(f"[CHAT] Q: {question[:50]}...")

        # Initialize metrics
        metrics = ChatMetrics()

        # Guardrails check
        guardrails_checked = False
        guardrails_safe = True
        blocked_category = None

        if self._use_guardrails:
            guardrails_checked = True
            guard_result = guard(question, use_llm_injection=True)
            guardrails_safe = guard_result.safe
            if not guard_result.safe:
                blocked_category = (
                    guard_result.injection.category
                    if guard_result.injection
                    else "validation"
                )
                logger.warning(f"[CHAT] Blocked by guardrails: {guard_result.message}")
                metrics.guardrails = GuardrailsMetrics(
                    checked=True,
                    safe=False,
                    blocked_category=blocked_category,
                )
                return ChatResponse(
                    answer=guard_result.message,
                    intent="rag",
                    status="blocked",
                    metrics=metrics,
                )

        metrics.guardrails = GuardrailsMetrics(
            checked=guardrails_checked,
            safe=guardrails_safe,
            blocked_category=blocked_category,
        )

        detected_intent = route(question, intent=intent)
        logger.info(f"[CHAT] Intent: {detected_intent}")

        if detected_intent == "chat":
            # Simple chat - direct LLM call with conversation history
            messages = self._build_chat_messages(question)
            response = self.llm.generate_sync(
                messages,
                cache_system=self._llm_caching_enabled,
            )
            metrics.add_llm_usage(response.usage)
            answer = response.content
            status = "success"
            agent_metrics = AgentMetrics(agent_type="chat", iterations=1)
        elif detected_intent == "rag":
            result = self.orchestrator.run(question)
            # Collect LLM usages from orchestrator
            for usage in result.llm_usages:
                metrics.add_llm_usage(usage)
            agent_metrics = AgentMetrics(
                agent_type="orchestrator",
                iterations=result.iteration,
            )
            answer = result.answer or "Nu am putut genera un răspuns."
            status = result.status
        else:  # sql
            result = self.analyst.run(question)
            # Collect LLM usages from analyst
            for usage in result.llm_usages:
                metrics.add_llm_usage(usage)
            # Extract SQL query from the last successful step
            sql_query = None
            for step_result in result.step_results:
                if step_result.action == "query" and step_result.status == "success":
                    # Get SQL from the corresponding step
                    for step in result.plan:
                        if hasattr(step, "table") and step.id == step_result.step_id:
                            # The actual SQL would be in the NL2SQL agent state
                            # For now, we note the step was executed
                            pass
            agent_metrics = AgentMetrics(
                agent_type="analyst",
                iterations=1,
                steps_count=len(result.plan),
                sql_query=sql_query,
            )
            answer = result.answer or "Nu am putut genera un răspuns."
            status = result.status

        metrics.agent = agent_metrics

        # Memory metrics and save
        messages_count = 0
        if self._memory_enabled:
            # Always keep in-memory history when memory is enabled
            self._history.append({"role": "user", "content": question})
            self._history.append({"role": "assistant", "content": answer})
            messages_count = len(self._history)

            # Additionally persist to DB if enabled
            if self._persist:
                with transaction() as session:
                    memory = ConversationMemory(self._session_id, session)
                    if self._session_id is None:
                        self._session_id = memory.session_id
                    memory.add_exchange(question, answer)

        metrics.memory = MemoryMetrics(
            messages_count=messages_count,
            session_id=self._session_id,
        )

        logger.info(f"[CHAT] Status: {status}")
        return ChatResponse(
            answer=answer,
            intent=detected_intent,
            status=status,
            metrics=metrics,
        )

    def _build_chat_messages(self, question: str) -> list[dict]:
        """Build messages for direct chat with conversation history."""
        messages = []

        # Add system context if LLM caching is enabled
        if self._llm_caching_enabled and self._llm_caching_context:
            messages.append({"role": "system", "content": self._llm_caching_context})
        else:
            # Default system prompt for chat
            messages.append({
                "role": "system",
                "content": "Ești un asistent AI util și prietenos. Răspunde concis și clar în limba în care ți se adresează utilizatorul.",
            })

        # Add conversation history
        for msg in self._history:
            messages.append(msg)

        # Add current question
        messages.append({"role": "user", "content": question})

        return messages

    def get_system_prompt(self) -> str:
        """Generează system prompt cu istoric."""
        return self.prompts.render("qa_system", history=self.history)

    def clear_history(self) -> int:
        """Șterge istoricul conversației."""
        if self._persist:
            with transaction() as session:
                memory = ConversationMemory(self._session_id, session)
                deleted = memory.clear()
                logger.info(f"[CHAT] Cleared {deleted} messages from DB")
                return deleted
        else:
            count = len(self._history)
            self._history.clear()
            logger.info(f"[CHAT] Cleared {count} messages from memory")
            return count
