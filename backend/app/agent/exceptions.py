from __future__ import annotations


class AgentError(RuntimeError):
    """Base class for agent runtime failures."""


class AgentUnavailableError(AgentError):
    """The underlying model/runtime could not produce an answer."""


class AgentTimeoutError(AgentError):
    """The agent exceeded the allotted time."""


class MissingPdfContextError(AgentError):
    """The agent was invoked without a pdf_id in the RunnableConfig."""
