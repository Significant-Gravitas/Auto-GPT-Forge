import asyncio
import typing

from fastapi import APIRouter, FastAPI
from hypercorn.asyncio import serve
from hypercorn.config import Config

from .db import AgentDB
from .middlewares import AgentMiddleware
from .routes import base_router
from .schema import Step, Task
from .workspace import Workspace


class Agent:
    def __init__(self, database: AgentDB, workspace: Workspace):
        self.db = database
        self.workspace = workspace

    def start(self, port: int = 8000, router: APIRouter = base_router):
        """
        Start the agent server.
        """
        config = Config()
        config.bind = [f"localhost:{port}"]
        app = FastAPI(
            title="Auto-GPT Forge",
            description="Modified version of The Agent Protocol.",
            version="v0.4",
        )
        app.include_router(router)
        app.add_middleware(AgentMiddleware, agent=self)
        asyncio.run(serve(app, config))

    def create_task(self, task: Task) -> Task:
        """
        Create a task for the agent.
        """
        raise NotImplementedError

    def list_tasks(self) -> typing.List[str]:
        """
        List the IDs of all tasks that the agent has created.
        """
        raise NotImplementedError

    def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID.
        """
        raise NotImplementedError

    def list_steps(self, task_id: str) -> typing.List[str]:
        """
        List the IDs of all steps that the task has created.
        """
        raise NotImplementedError

    def create_and_execute_step(self, task_id: str, step: Step) -> Step:
        """
        Create a step for the task.
        """
        raise NotImplementedError

    def get_step(self, task_id: str, step_id: str) -> Step:
        """
        Get a step by ID.
        """
        raise NotImplementedError

    def list_artifacts(self, task_id: str) -> typing.List[Artifact]:
        """
        List the artifacts that the task has created.
        """
        raise NotImplementedError

    def create_artifact(self, task_id: str, artifact: Artifact) -> Artifact:
        """
        Create an artifact for the task.
        """
        raise NotImplementedError

    def get_artifact(self, task_id: str, artifact_id: str) -> Artifact:
        """
        Get an artifact by ID.
        """
        raise NotImplementedError
