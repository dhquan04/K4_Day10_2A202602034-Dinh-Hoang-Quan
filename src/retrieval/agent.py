from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    tool_calls: list[str]
    tool_outputs: list[dict[str, str]]


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            elif getattr(block, "text", None):
                parts.append(str(block.text))
        return "\n".join(parts)
    return str(content)


def build_agent(settings: Settings, index: LocalEmbeddingIndex):
    @tool
    def semantic_search_papers(query: str, top_k: int = 4) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        results = index.search(query, top_k=top_k)
        lines = []
        for result in results:
            lines.append(
                f"paper_id: {result.paper_id}\n"
                f"title: {result.title}\n"
                f"score: {result.score:.4f}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or exact title from the local corpus."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return (
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"{record['content']}"
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=(
            "You answer questions about the indexed scholarly paper corpus sourced from Crossref. "
            "Use tools before answering factual questions. "
            "If the indexed corpus does not support the answer, say so clearly."
        ),
        name="paper_corpus_agent",
    )


def run_agent_with_trace(agent: Any, question: str) -> AgentRunResult:
    """Run one agent turn and retain evidence that retrieval tools were used."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return AgentRunResult(answer="", tool_calls=[], tool_outputs=[])

    tool_calls: list[str] = []
    tool_outputs: list[dict[str, str]] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if name:
                tool_calls.append(str(name))
        if getattr(message, "type", "") == "tool":
            tool_outputs.append(
                {
                    "name": str(getattr(message, "name", "unknown")),
                    "content": _content_text(getattr(message, "content", "")),
                }
            )

    final_message = messages[-1]
    answer = _content_text(getattr(final_message, "content", str(final_message)))
    return AgentRunResult(
        answer=answer,
        tool_calls=tool_calls,
        tool_outputs=tool_outputs,
    )


def run_agent_question(agent: Any, question: str) -> str:
    return run_agent_with_trace(agent, question).answer
