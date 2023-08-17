import os

from agent_protocol import Agent
from dotenv import load_dotenv
import autogpt.agent
import autogpt.db
from autogpt.benchmark_integration import add_benchmark_routes

if __name__ == "__main__":
    """Runs the agent server"""
    load_dotenv()
    router = add_benchmark_routes()

    database_name = os.getenv("DATABASE_STRING")
    print(database_name)
    port = os.getenv("PORT")
    workspace = os.getenv("AGENT_WORKSPACE")
    auto_gpt = autogpt.agent.AutoGPT()

    database = autogpt.db.AgentDB(database_name)
    agent = Agent.setup_agent(auto_gpt.task_handler, auto_gpt.step_handler)
    agent.db = database
    agent.workspace = workspace
    agent.start(port=port, router=router)
