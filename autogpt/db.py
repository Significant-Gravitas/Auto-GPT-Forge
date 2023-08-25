"""
This is an example implementation of the Agent Protocol DB for development Purposes
It uses SQLite as the database and file store backend.
IT IS NOT ADVISED TO USE THIS IN PRODUCTION!
"""

import datetime
import math
import uuid
from typing import Dict, List, Optional, Tuple

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, joinedload, relationship, sessionmaker

from .errors import NotFoundError
from .forge_log import CustomLogger
from .schema import Artifact, Pagination, Status, Step, Task, TaskInput

LOG = CustomLogger(__name__)


class Base(DeclarativeBase):
    pass


class TaskModel(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    input = Column(String)
    additional_input = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    artifacts = relationship("ArtifactModel", back_populates="task")


class StepModel(Base):
    __tablename__ = "steps"

    step_id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.task_id"))
    name = Column(String)
    input = Column(String)
    status = Column(String)
    is_last = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    additional_properties = Column(String)
    artifacts = relationship("ArtifactModel", back_populates="step")


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    artifact_id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.task_id"))
    step_id = Column(String, ForeignKey("steps.step_id"))
    agent_created = Column(Boolean, default=False)
    file_name = Column(String)
    uri = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    step = relationship("StepModel", back_populates="artifacts")
    task = relationship("TaskModel", back_populates="artifacts")


def convert_to_task(task_obj: TaskModel, debug_enabled: bool = False) -> Task:
    if debug_enabled:
        LOG.debug(f"Converting TaskModel to Task for task_id: {task_obj.task_id}")
    task_artifacts = [convert_to_artifact(artifact) for artifact in task_obj.artifacts]
    return Task(
        task_id=task_obj.task_id,
        created_at=task_obj.created_at,
        modified_at=task_obj.modified_at,
        input=task_obj.input,
        additional_input=task_obj.additional_input,
        artifacts=task_artifacts,
    )


def convert_to_step(step_model: StepModel, debug_enabled: bool = False) -> Step:
    if debug_enabled:
        LOG.debug(f"Converting StepModel to Step for step_id: {step_model.step_id}")
    step_artifacts = [
        convert_to_artifact(artifact) for artifact in step_model.artifacts
    ]
    status = Status.completed if step_model.status == "completed" else Status.created
    return Step(
        task_id=step_model.task_id,
        step_id=step_model.step_id,
        created_at=step_model.created_at,
        modified_at=step_model.modified_at,
        name=step_model.name,
        input=step_model.input,
        status=status,
        artifacts=step_artifacts,
        is_last=step_model.is_last == 1,
        additional_properties=step_model.additional_properties,
    )


def convert_to_artifact(artifact_model: ArtifactModel) -> Artifact:
    return Artifact(
        artifact_id=artifact_model.artifact_id,
        created_at=artifact_model.created_at,
        modified_at=artifact_model.modified_at,
        agent_created=artifact_model.agent_created,
        uri=artifact_model.uri,
    )


# sqlite:///{database_name}
class AgentDB:
    def __init__(self, database_string, debug_enabled: bool = False) -> None:
        super().__init__()
        self.debug_enabled = debug_enabled
        if self.debug_enabled:
            LOG.debug(f"Initializing AgentDB with database_string: {database_string}")
        self.engine = create_engine(database_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    async def create_task(
        self, input: Optional[str], additional_input: Optional[TaskInput] = None
    ) -> Task:
        if self.debug_enabled:
            LOG.debug("Creating new task")
        with self.Session() as session:
            try:
                new_task = TaskModel(
                    task_id=str(uuid.uuid4()),
                    input=input,
                    additional_input=additional_input.__root__
                    if additional_input
                    else None,
                )
                session.add(new_task)
                session.commit()
                session.refresh(new_task)
                if self.debug_enabled:
                    LOG.debug(f"Created new task with task_id: {new_task.task_id}")
                return convert_to_task(new_task, self.debug_enabled)
            except SQLAlchemyError as e:
                LOG.error(f"SQLAlchemy error while creating task: {e}")
                raise
            except Exception as e:
                LOG.error(f"Unexpected error while creating task: {e}")
                raise

    async def create_step(
        self,
        task_id: str,
        input: str,
        is_last: bool = False,
        additional_properties: Optional[Dict[str, str]] = None,
    ) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Creating new step for task_id: {task_id}")
        try:
            session = self.Session()
            new_step = StepModel(
                task_id=task_id,
                step_id=str(uuid.uuid4()),
                name=input,
                input=input,
                status="created",
                is_last=is_last,
                additional_properties=additional_properties,
            )
            session.add(new_step)
            session.commit()
            session.refresh(new_step)
            if self.debug_enabled:
                LOG.debug(f"Created new step with step_id: {new_step.step_id}")
            return convert_to_step(new_step, self.debug_enabled)
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while creating step: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while creating step: {e}")
            raise

    async def create_artifact(
        self,
        task_id: str,
        file_name: str,
        uri: str,
        agent_created: bool = False,
        step_id: str | None = None,
    ) -> Artifact:
        if self.debug_enabled:
            LOG.debug(f"Creating new artifact for task_id: {task_id}")
        try:
            session = self.Session()
            if (
                existing_artifact := session.query(ArtifactModel)
                .filter_by(uri=uri)
                .first()
            ):
                session.close()
                if self.debug_enabled:
                    LOG.debug(f"Artifact already exists with uri: {uri}")
                return convert_to_artifact(existing_artifact)

            new_artifact = ArtifactModel(
                artifact_id=str(uuid.uuid4()),
                task_id=task_id,
                step_id=step_id,
                agent_created=agent_created,
                file_name=file_name,
                uri=uri,
            )
            session.add(new_artifact)
            session.commit()
            session.refresh(new_artifact)
            if self.debug_enabled:
                LOG.debug(
                    f"Created new artifact with artifact_id: {new_artifact.artifact_id}"
                )
            return convert_to_artifact(new_artifact)
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while creating step: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while creating step: {e}")
            raise

    async def get_task(self, task_id: int) -> Task:
        """Get a task by its id"""
        if self.debug_enabled:
            LOG.debug(f"Getting task with task_id: {task_id}")
        session = self.Session()
        try:
            if task_obj := (
                session.query(TaskModel)
                .options(joinedload(TaskModel.artifacts))
                .filter_by(task_id=task_id)
                .first()
            ):
                return convert_to_task(task_obj, self.debug_enabled)
            else:
                LOG.error(f"Task not found with task_id: {task_id}")
                raise NotFoundError("Task not found")
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting task: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting task: {e}")
            raise

    async def get_step(self, task_id: int, step_id: int) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Getting step with task_id: {task_id} and step_id: {step_id}")
        try:
            session = self.Session()
            if step := (
                session.query(StepModel)
                .options(joinedload(StepModel.artifacts))
                .filter(StepModel.step_id == step_id)
                .first()
            ):
                return convert_to_step(step, self.debug_enabled)

            else:
                LOG.error(
                    f"Step not found with task_id: {task_id} and step_id: {step_id}"
                )
                raise NotFoundError("Step not found")
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting step: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting step: {e}")
            raise

    async def update_step(
        self,
        task_id: str,
        step_id: str,
        status: str,
        additional_properties: Optional[Dict[str, str]] = None,
    ) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Updating step with task_id: {task_id} and step_id: {step_id}")
        try:
            session = self.Session()
            if (
                step := session.query(StepModel)
                .filter_by(task_id=task_id, step_id=step_id)
                .first()
            ):
                step.status = status
                step.additional_properties = additional_properties
                session.commit()
                return await self.get_step(task_id, step_id)
            else:
                LOG.error(
                    f"Step not found for update with task_id: {task_id} and step_id: {step_id}"
                )
                raise NotFoundError("Step not found")
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting step: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting step: {e}")
            raise

    async def get_artifact(self, artifact_id: str) -> Artifact:
        if self.debug_enabled:
            LOG.debug(f"Getting artifact with and artifact_id: {artifact_id}")
        try:
            session = self.Session()
            if (
                artifact_model := session.query(ArtifactModel)
                .filter_by(artifact_id=artifact_id)
                .first()
            ):
                return convert_to_artifact(artifact_model)
            else:
                LOG.error(f"Artifact not found with and artifact_id: {artifact_id}")
                raise NotFoundError("Artifact not found")
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting artifact: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting artifact: {e}")
            raise

    async def list_tasks(
        self, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Task], Pagination]:
        if self.debug_enabled:
            LOG.debug("Listing tasks")
        session = self.Session()
        try:
            tasks = (
                session.query(TaskModel)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            if not tasks:
                raise NotFoundError("No tasks found")
            total = session.query(TaskModel).count()
            pages = math.ceil(total / per_page)
            pagination = Pagination(
                total_items=total,
                total_pages=pages,
                current_page=page,
                page_size=per_page,
            )
            return [
                convert_to_task(task, self.debug_enabled) for task in tasks
            ], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing tasks: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing tasks: {e}")
            raise

    async def list_steps(
        self, task_id: str, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Step], Pagination]:
        if self.debug_enabled:
            LOG.debug(f"Listing steps for task_id: {task_id}")
        session = self.Session()
        try:
            steps = (
                session.query(StepModel)
                .filter_by(task_id=task_id)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            if not steps:
                raise NotFoundError("No steps found")
            total = session.query(StepModel).filter_by(task_id=task_id).count()
            pages = math.ceil(total / per_page)
            pagination = Pagination(
                total_items=total,
                total_pages=pages,
                current_page=page,
                page_size=per_page,
            )
            return [
                convert_to_step(step, self.debug_enabled) for step in steps
            ], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing steps: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing steps: {e}")
            raise

    async def list_artifacts(
        self, task_id: str, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Artifact], Pagination]:
        if self.debug_enabled:
            LOG.debug(f"Listing artifacts for task_id: {task_id}")
        session = self.Session()
        try:
            artifacts = (
                session.query(ArtifactModel)
                .filter_by(task_id=task_id)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            if not artifacts:
                raise NotFoundError("No artifacts found")
            total = session.query(ArtifactModel).filter_by(task_id=task_id).count()
            pages = math.ceil(total / per_page)
            pagination = Pagination(
                total_items=total,
                total_pages=pages,
                current_page=page,
                page_size=per_page,
            )
            return [convert_to_artifact(artifact) for artifact in artifacts], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing artifacts: {e}")
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing artifacts: {e}")
            raise
