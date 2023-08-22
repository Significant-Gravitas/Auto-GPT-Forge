import asyncio
import os
import typing

from fastapi import APIRouter, FastAPI, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from hypercorn.asyncio import serve
from hypercorn.config import Config

from .db import AgentDB
from .middlewares import AgentMiddleware
from .routes.agent_protocol import base_router
from .schema import Artifact, Status, Step, StepRequestBody, Task, TaskRequestBody
from .utils import run
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

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        """
        Create a task for the agent.
        """
        try:
            task = await self.db.create_task(
                input=task_request.input if task_request.input else None,
                additional_input=task_request.additional_input
                if task_request.additional_input
                else None,
            )
            print(task)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        print(task)
        return task

    async def list_tasks(
        self, page: int = 1, pageSize: int = 10
    ) -> typing.Dict[str, typing.Any]:
        """
        List all tasks that the agent has created.
        """
        try:
            tasks, pagination = await self.db.list_tasks(page, pageSize)
            tasks = [task.dict() for task in tasks]
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return JSONResponse(
            content={"items": tasks, "pagination": pagination.dict()}, status_code=200
        )

    async def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID.
        """
        if not task_id:
            return Response(status_code=400, content="Task ID is required.")
        if not isinstance(task_id, str):
            return Response(status_code=400, content="Task ID must be a string.")
        try:
            task = await self.db.get_task(task_id)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return task

    async def list_steps(
        self, task_id: str, page: int = 1, pageSize: int = 10
    ) -> typing.Dict[str, typing.Any]:
        """
        List the IDs of all steps that the task has created.
        """
        if not task_id:
            return Response(status_code=400, content="Task ID is required.")
        if not isinstance(task_id, str):
            return Response(status_code=400, content="Task ID must be a string.")
        try:
            steps, pagination = await self.db.list_steps(task_id, page, pageSize)
            steps_ids = [step.step_id for step in steps]
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return {"items": steps_ids, "pagination": pagination.dict()}

    async def create_and_execute_step(
        self, task_id: str, step_request: StepRequestBody
    ) -> Step:
        """
        Create a step for the task.
        """
        if step_request.input != "y":
            step = await self.db.create_step(
                task_id=task_id,
                input=step_request.input if step_request else None,
                additional_properties=step_request.additional_input
                if step_request
                else None,
            )
            # utils.run
            artifacts = run(step.input)
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
                ), f"Artifact not instance of Artifact {type(art)}"
                step.artifacts.append(art)
            step.status = "completed"
        else:
            steps, steps_pagination = await self.db.list_steps(
                task_id, page=1, per_page=100
            )
            artifacts, artifacts_pagination = await self.db.list_artifacts(
                task_id, page=1, per_page=100
            )
            step = steps[-1]
            step.artifacts = artifacts
            step.output = "No more steps to run."
            # The step is the last step on this page so checking if this is the
            # last page is sufficent to know if it is the last step
            step.is_last = steps_pagination.current == steps_pagination.pages
        if isinstance(step.status, Status):
            step.status = step.status.value
        step.output = "Done some work"
        return JSONResponse(content=step.dict(), status_code=200)

    async def get_step(self, task_id: str, step_id: str) -> Step:
        """
        Get a step by ID.
        """
        if not task_id or not step_id:
            return Response(
                status_code=400, content="Task ID and step ID are required."
            )
        if not isinstance(task_id, str) or not isinstance(step_id, str):
            return Response(
                status_code=400, content="Task ID and step ID must be strings."
            )
        try:
            step = await self.db.get_step(task_id, step_id)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return step

    async def list_artifacts(
        self, task_id: str, page: int = 1, pageSize: int = 10
    ) -> typing.Dict[str, typing.Any]:
        """
        List the artifacts that the task has created.
        """
        if not task_id:
            return Response(status_code=400, content="Task ID is required.")
        if not isinstance(task_id, str):
            return Response(status_code=400, content="Task ID must be a string.")
        try:
            artifacts, pagination = await self.db.list_artifacts(
                task_id, page, pageSize
            )
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return JSONResponse(
            content={"items": artifacts, "pagination": pagination.dict()},
            status_code=200,
        )

    async def create_artifact(
        self,
        task_id: str,
        file: UploadFile | None = None,
        uri: str | None = None,
    ) -> Artifact:
        """
        Create an artifact for the task.
        """
        if not file and not uri:
            return Response(status_code=400, content="No file or uri provided")
        data = None
        if not uri:
            file_name = file.filename or str(uuid4())
            try:
                data = b""
                while contents := file.file.read(1024 * 1024):
                    data += contents
            except Exception as e:
                return Response(status_code=500, content=str(e))
        else:
            try:
                data = await self.load_from_uri(uri, task_id)
                file_name = uri.split("/")[-1]
            except Exception as e:
                return Response(status_code=500, content=str(e))

        file_path = os.path.join(task_id / file_name)
        self.write(file_path, data)
        self.db.save_artifact(task_id, artifact)

        artifact = await self.create_artifact(
            task_id=task_id,
            file_name=file_name,
            uri=f"file://{file_path}",
            agent_created=False,
        )

        return artifact

    async def load_from_uri(self, uri: str, task_id: str) -> bytes:
        """
        Load file from given URI and return its bytes.
        """
        file_path = None
        try:
            if uri.startswith("file://"):
                file_path = uri.split("file://")[1]
                if not self.workspace.exists(task_id, file_path):
                    return Response(status_code=500, content="File not found")
                return self.workspace.read(task_id, file_path)
            # elif uri.startswith("s3://"):
            #     import boto3

            #     s3 = boto3.client("s3")
            #     bucket_name, key_name = uri[5:].split("/", 1)
            #     file_path = "/tmp/" + task_id
            #     s3.download_file(bucket_name, key_name, file_path)
            #     with open(file_path, "rb") as f:
            #         return f.read()
            # elif uri.startswith("gs://"):
            #     from google.cloud import storage

            #     storage_client = storage.Client()
            #     bucket_name, blob_name = uri[5:].split("/", 1)
            #     bucket = storage_client.bucket(bucket_name)
            #     blob = bucket.blob(blob_name)
            #     file_path = "/tmp/" + task_id
            #     blob.download_to_filename(file_path)
            #     with open(file_path, "rb") as f:
            #         return f.read()
            # elif uri.startswith("https://"):
            #     from azure.storage.blob import BlobServiceClient

            #     blob_service_client = BlobServiceClient.from_connection_string(
            #         "my_connection_string"
            #     )
            #     container_name, blob_name = uri[8:].split("/", 1)
            #     blob_client = blob_service_client.get_blob_client(
            #         container_name, blob_name
            #     )
            #     file_path = "/tmp/" + task_id
            #     with open(file_path, "wb") as download_file:
            #         download_file.write(blob_client.download_blob().readall())
            #     with open(file_path, "rb") as f:
            #         return f.read()
            else:
                return Response(status_code=500, content="Loading from unsupported uri")
        except Exception as e:
            return Response(status_code=500, content=str(e))

    async def get_artifact(self, task_id: str, artifact_id: str) -> Artifact:
        """
        Get an artifact by ID.
        """
        try:
            artifact = await self.db.get_artifact(task_id, artifact_id)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        try:
            retrieved_artifact = await self.load_from_uri(artifact.uri, artifact_id)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        path = artifact.file_name
        try:
            with open(path, "wb") as f:
                f.write(retrieved_artifact)
        except Exception as e:
            return Response(status_code=500, content=str(e))
        return FileResponse(
            # Note: mimetype is guessed in the FileResponse constructor
            path=path,
            filename=artifact.file_name,
        )
