import time

import autogpt.utils
from autogpt.agent_protocol import Agent, Artifact, Step, Task, TaskDB


class AutoGPT(Agent):
    def __init__(self, db: TaskDB) -> None:
        super().__init__(db)

    async def create_task(self, task: Task) -> None:
        print(f"task: {task.input}")
        await Agent.db.create_step(task.task_id, task.input, is_last=True)
        time.sleep(2)

        autogpt.utils.run(
            task.input
        )  # the task_handler only creates the task, it doesn't execute it
        # print(f"Created Task id: {task.task_id}")
        return task

    async def run_step(self, step: Step) -> Step:
        # print(f"step: {step}")
        agent_step = await Agent.db.get_step(step.task_id, step.step_id)
        updated_step: Step = await Agent.db.update_step(
            agent_step.task_id, agent_step.step_id, status="completed"
        )
        updated_step.output = agent_step.input
        if step.is_last:
            print(f"Task completed: {updated_step.task_id}")
        else:
            print(f"Step completed: {updated_step}")
        return updated_step

    async def retrieve_artifact(self, task_id: str, artifact: Artifact) -> Artifact:
        """
        Retrieve the artifact data from wherever it is stored and return it as bytes.
        """
        return artifact

    async def save_artifact(self, task_id: str, artifact: Artifact) -> Artifact:
        """
        Save the artifact data to the agent's workspace, loading from uri if bytes are not available.
        """
        assert (
            artifact.data is not None and artifact.uri is not None
        ), "Artifact data or uri must be set"

        if artifact.data is None:
            self.db.save_artifact(task_id, artifact)

        return artifact
