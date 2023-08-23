import logging
import os

from dotenv import load_dotenv

import autogpt.agent
import autogpt.db
import autogpt.monitoring
from autogpt.benchmark_integration import add_benchmark_routes
from autogpt.workspace import LocalWorkspace

if __name__ == "__main__":
    """Runs the agent server"""
    load_dotenv()

    autogpt.monitoring.setup_logger(json_format=False)
    router = add_benchmark_routes()

    database_name = os.getenv("DATABASE_STRING")
    workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE"))
    port = os.getenv("PORT")
    logging.debug("Debug level test message")
    logging.info("Info level test message")
    logging.warning("Warning level test message")
    logging.error("Error level test message")
    logging.critical("Critical level test message")

    database = autogpt.db.AgentDB(database_name, debug_enabled=True)
    agent = autogpt.agent.Agent(database=database, workspace=workspace)

    agent.start(port=port, router=router)
