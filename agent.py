"""ADK Entrypoint Module exposing `root_agent` for `adk web`, `adk run`, and `agents-cli`."""

from .orchestrator import EnterpriseDealCoordinatorAgent, global_coordinator_agent, root_agent

__all__ = ["root_agent", "global_coordinator_agent", "EnterpriseDealCoordinatorAgent"]
