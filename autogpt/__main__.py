import agent_protocol
from agent_protocol import router
from dotenv import load_dotenv
from fastapi import APIRouter, Response

import autogpt.agent

e2b_extension_router = APIRouter()


@e2b_extension_router.get("/hb")
async def hello():
    return Response("Agent running")


e2b_extension_router.include_router(router)

if __name__ == "__main__":
    """Runs the agent server"""
    load_dotenv()
    agent_protocol.Agent.setup_agent(
        autogpt.agent.task_handler, autogpt.agent.step_handler
    ).start(port=8915, router=e2b_extension_router)
