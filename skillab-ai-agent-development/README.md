# Skillab — AI Agent Development

Homeworks and course materials (lessons 1–12, in [course_materials/lesson](course_materials/lesson/)) from the Skillab AI agents course.

## Homeworks

- **[homework_1](homework/homework_1/)** — a question-answering ReAct agent with custom Pydantic tools (calculator, date/time, web search) and YAML prompts.
- **[homework_2](homework/homework_2/)** — a document-analyst agent that extracts invoices/contracts, stores them in PostgreSQL/pgvector, and answers questions grounded in them via RAG.
- **[homework_3](homework/homework_3/)** — a multi-agent system (LangGraph) with two hierarchical agents: an Orchestrator+RAG that searches documents with a self-correcting feedback loop, and an Analyst+NL2SQL that plans and runs SQL queries over a database.
- **[homework_4](homework/homework_4/)** — agent with memory, caching and intent classifier (tranined with sklearn)  
- **[homework_5](homework/homework_5/)** — a FastMCP server that exposes the homework_3 agents (data analyst / NL2SQL and orchestrator / RAG) as MCP tools, with guardrails.

