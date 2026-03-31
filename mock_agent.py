from __future__ import annotations
import asyncio
import random
from agentbench.adapter import AgentAdapter

class MockAgent(AgentAdapter):
    """A mock agent for demonstration purposes."""
    
    def setup(self) -> None:
        pass
        
    async def run(self, task_input: str) -> str:
        # Simulate some processing time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Simple logic to pass some criteria
        if "weather" in task_input.lower():
            return "The weather in Tokyo is 22 degrees Celsius and sunny."
        if "NVDA" in task_input:
            return "NVDA is trading at $135.20, while MSFT is at $420.15."
        if "LangGraph" in task_input:
            return "LangGraph is a graph-based orchestration framework, while CrewAI uses a role-based approach. LangGraph offers more control for complex cycles."
        
        return "I have processed your request: " + task_input
        
    def teardown(self) -> None:
        pass
