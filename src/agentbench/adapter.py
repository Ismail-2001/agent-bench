"""Agent adapter interface — the bridge between agentbench and your agent."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AgentAdapter(ABC):
    """
    Base class for connecting any agent to agentbench.

    Subclass this and implement `run()` to benchmark your agent.
    Override `run_conversation()` for multi-turn evaluation.

    Example::

        class MyAgent(AgentAdapter):
            def setup(self):
                self.agent = create_my_agent()

            async def run(self, task_input: str) -> str:
                return await self.agent.ainvoke(task_input)
    """

    def setup(self) -> None:
        """Initialize the agent. Called once before all tasks."""

    @abstractmethod
    async def run(self, task_input: str) -> str:
        """
        Run the agent on a single input and return the output as a string.

        This is the only method you MUST implement.

        Args:
            task_input: The task prompt / user message.

        Returns:
            The agent's output as a plain string.
        """
        ...

    async def run_conversation(self, messages: list[dict]) -> str:
        """
        Run the agent on a multi-turn conversation.

        Override this for agents that support multi-turn interactions.
        Default implementation sends only the last user message.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.

        Returns:
            The agent's final output as a plain string.
        """
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg["content"]
                break
        return await self.run(last_user_msg)

    def teardown(self) -> None:
        """Cleanup. Called once after all tasks."""
