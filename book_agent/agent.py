# book_agent/agent.py
"""
Parallel-only Kindle book workflow.
Runs:
1. outline_agent_parallel  (cloned outline agent)
2. chapter_parallel_agent  (ParallelAgent running cloned chapter writer agents)
"""

from google.adk.agents import SequentialAgent, ParallelAgent
from .custom_agents import (
    outline_agent,
    chapter_writer_agents,
)


# ------------------------------------------------------------
# Helper to clone agents (avoid parent-agent conflicts)
# ------------------------------------------------------------

def clone_agent(agent, new_name: str):
    return type(agent)(
        name=new_name,
        model=agent.model,
        description=agent.description,
        instruction=agent.instruction,
        tools=agent.tools.copy() if agent.tools else [],
        sub_agents=[]
    )


# ------------------------------------------------------------
# Clone outline agent for exclusive use in the parallel workflow
# ------------------------------------------------------------

outline_agent_parallel = clone_agent(outline_agent, "outline_agent_parallel")


# ------------------------------------------------------------
# Clone chapter writer agents for parallel run
# ------------------------------------------------------------

chapter_writers_parallel = [
    clone_agent(agent, f"{agent.name}_parallel")
    for agent in chapter_writer_agents
]


# ------------------------------------------------------------
# Parallel agent: runs all chapter writers at the same time
# ------------------------------------------------------------

chapter_parallel_agent = ParallelAgent(
    name="chapter_parallel_agent",
    description="Runs chapter writer agents in parallel.",
    sub_agents=chapter_writers_parallel,
)


# ------------------------------------------------------------
# Build the entire workflow:
# outline → (parallel) chapters
# ------------------------------------------------------------

parallel_book_demo_agent = SequentialAgent(
    name="parallel_book_demo_agent",
    description="Parallel-only pipeline: outline → chapter writers.",
    sub_agents=[
        outline_agent_parallel,
        chapter_parallel_agent,
    ],
)


# ------------------------------------------------------------
# Root agent for ADK app
# ------------------------------------------------------------

root_agent = parallel_book_demo_agent
