import os

import autogpt.utils
from autogpt.agent_protocol import Agent, Artifact, Step, Task, TaskDB

from .workspace import Workspace

# class Agent:

#     def create_task(self, task: Task) -> Task:
#         """
#         Create a task for the agent.
#         """
#         raise NotImplementedError

#     def list_tasks(self) -> List[str]:
#         """
#         List the IDs of all tasks that the agent has created.
#         """
#         raise NotImplementedError


#     def get_task(self, task_id: str) -> Task:
#         """
#         Get a task by ID.
#         """
#         raise NotImplementedError

#     def list_steps(self, task_id: str) -> List[str]:
#         """
#         List the IDs of all steps that the task has created.
#         """
#         raise NotImplementedError

#     def create_and_execute_step(self, task_id: str, step: Step) -> Step:
#         """
#         Create a step for the task.
#         """
#         raise NotImplementedError

#     def get_step(self, task_id: str, step_id: str) -> Step:
#         """
#         Get a step by ID.
#         """
#         raise NotImplementedError

#     def list_artifacts(self, task_id: str) -> List[Artifact]:
#         """
#         List the artifacts that the task has created.
#         """
#         raise NotImplementedError


#     def create_artifact(self, task_id: str, artifact: Artifact) -> Artifact:
#         """
#         Create an artifact for the task.
#         """
#         raise NotImplementedError

#     def get_artifact(self, task_id: str, artifact_id: str) -> Artifact:
#         """
#         Get an artifact by ID.
#         """
#         raise NotImplementedError


class AutoGPT(Agent):
    def __init__(self, db: TaskDB, workspace: Workspace) -> None:
        super().__init__(db)
        self.workspace = workspace

    async def create_task(self, task: Task) -> None:
        print(f"task: {task.input}")
        return task

    async def run_step(self, step: Step) -> Step:
        artifacts = autogpt.utils.run(step.input)
        for artifact in artifacts:
            art = await self.db.create_artifact(
                task_id=step.task_id,
                file_name=artifact["file_name"],
                uri=artifact["uri"],
                agent_created=True,
                step_id=step.step_id,
            )
            assert isinstance(
                art, Artifact
            ), f"Artifact not isntance of Artifact {type(art)}"
            step.artifacts.append(art)
        step.status = "completed"
        return step

    async def retrieve_artifact(self, task_id: str, artifact: Artifact) -> bytes:
        """
        Retrieve the artifact data from wherever it is stored and return it as bytes.
        """
        if not artifact.uri.startswith("file://"):
            raise NotImplementedError("Loading from uri not implemented")
        file_path = artifact.uri.split("file://")[1]
        if not self.workspace.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found in workspace")
        return self.workspace.read(file_path)

    async def save_artifact(
        self, task_id: str, artifact: Artifact, data: bytes
    ) -> Artifact:
        """
        Save the artifact data to the agent's workspace, loading from uri if bytes are not available.
        """
        assert (
            data is not None and artifact.uri is not None
        ), "Data or Artifact uri must be set"

        if data is not None:
            file_path = os.path.join(task_id / artifact.file_name)
            self.write(file_path, data)
            artifact.uri = f"file://{file_path}"
            self.db.save_artifact(task_id, artifact)
        else:
            raise NotImplementedError("Loading from uri not implemented")

        return artifact
