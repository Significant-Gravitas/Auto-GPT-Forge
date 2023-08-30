from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlmodel.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship

from typing import List, Optional, Dict, Any, Tuple
from .schema import Task, Step, Artifact, Pagination, StepRequestBody
from .forge_log import ForgeLogger
from .errors import NotFoundError
import math
import uuid
LOG = ForgeLogger(__name__)


class TaskModel(Task, SQLModel, table=True):
    task_id: str = Field(default=None, primary_key=True)
    artifacts = relationship("ArtifactModel", back_populates="task")


class StepModel(Step, SQLModel, table=True):
    step_id: str = Field(default=None, primary_key=True)
    task_id: str = Field(default=None, foreign_key="tasks.task_id")


class ArtifactModel(Artifact, SQLModel, table=True):
    artifact_id: str = Field(default=None, primary_key=True)
    task_id: str = Field(default=None, foreign_key="tasks.task_id")
    step_id: str = Field(default=None, foreign_key="steps.step_id")

class AgentDB:
    def __init__(self, database_string: str) -> None:
        self.engine = create_engine(database_string, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)

    def create_task(self, task: Task) -> Task:
        if self.debug_enabled:
            LOG.debug("Creating new task")
        try:
            with Session(self.engine) as session:
                db_task = TaskModel(**task.dict())
                db_task.task_id = str(uuid.uuid4())
                session.add(db_task)
                session.commit()
                session.refresh(db_task)
                new_task = Task.parse_obj(db_task)
                if self.debug_enabled:
                    LOG.debug(f"Created new task with task_id: {new_task.task_id}")
                return new_task
        except Exception as e:
            LOG.error(f"Unexpected error while creating task: {e}")
            raise

    def list_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        with Session(self.engine) as session:
            tasks = session.exec(select(TaskModel).offset(skip).limit(limit)).all()
            return [Task.parse_obj(task) for task in tasks]
        
    
    async def create_step(
        self,
        task_id: str,
        input: StepRequestBody,
        is_last: bool = False,
        additional_input: Optional[Dict[str, Any]] = {},
    ) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Creating new step for task_id: {task_id}")
        try:
            with Session(self.engine) as session:
                new_step = StepModel(
                    task_id=task_id,
                    step_id=str(uuid.uuid4()),
                    name=input.input,
                    input=input.input,
                    status="created",
                    is_last=is_last,
                    additional_input=additional_input,
                )
                session.add(new_step)
                session.commit()
                session.refresh(new_step)
                if self.debug_enabled:
                    LOG.debug(f"Created new step with step_id: {new_step.step_id}")
                return Step.parse_obj(new_step)        
        except Exception as e:
            LOG.error(f"Unexpected error while creating step: {e}")
            raise

    
    async def create_artifact(
        self,
        task_id: str,
        file_name: str,
        relative_path: str,
        agent_created: bool = False,
        step_id: str | None = None,
    ) -> Artifact:
        if self.debug_enabled:
            LOG.debug(f"Creating new artifact for task_id: {task_id}")
        try:
            with Session(self.engine) as session:
                existing_artifact = session.query(ArtifactModel).filter_by(relative_path=relative_path, file_name=file_name).first()
                if existing_artifact:
                    if self.debug_enabled:
                        LOG.debug(
                            f"Artifact already exists with relative_path: {relative_path}"
                        )
                    return Artifact.parse_obj(existing_artifact)

                new_artifact = ArtifactModel(
                    artifact_id=str(uuid.uuid4()),
                    task_id=task_id,
                    step_id=step_id,
                    agent_created=agent_created,
                    file_name=file_name,
                    relative_path=relative_path,
                )
                session.add(new_artifact)
                session.commit()
                session.refresh(new_artifact)
                if self.debug_enabled:
                    LOG.debug(
                        f"Created new artifact with artifact_id: {new_artifact.artifact_id}"
                    )
                return Artifact.parse_obj(new_artifact)
        except Exception as e:
            LOG.error(f"Unexpected error while creating artifact: {e}")
            raise

    async def get_task(self, task_id: int) -> Task:
        """Get a task by its id"""
        if self.debug_enabled:
            LOG.debug(f"Getting task with task_id: {task_id}")
        try:
            with Session(self.engine) as session:
                task_obj = session.get(TaskModel, task_id)
                if task_obj is None:
                    LOG.error(f"Task not found with task_id: {task_id}")
                    raise NotFoundError("Task not found")
                artifacts = session.exec(select(ArtifactModel).where(ArtifactModel.task_id == task_id)).all()
                task = Task.parse_obj(task_obj)
                task.artifacts = [Artifact.parse_obj(artifact) for artifact in artifacts]
                return task
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting task: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting task: {e}")
            raise

    async def get_step(self, task_id: int, step_id: int) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Getting step with task_id: {task_id} and step_id: {step_id}")
        try:
            with Session(self.engine) as session:
                step_obj = session.get(StepModel, step_id)
                if step_obj is None:
                    LOG.error(
                        f"Step not found with task_id: {task_id} and step_id: {step_id}"
                    )
                    raise NotFoundError("Step not found")
                return Step.parse_obj(step_obj)
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting step: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting step: {e}")
            raise

    async def update_step(
        self,
        task_id: str,
        step_id: str,
        status: str,
        additional_input: Optional[Dict[str, Any]] = {},
    ) -> Step:
        if self.debug_enabled:
            LOG.debug(f"Updating step with task_id: {task_id} and step_id: {step_id}")
        try:
            with Session(self.engine) as session:
                step = session.get(StepModel, step_id)
                if step is None:
                    LOG.error(
                        f"Step not found for update with task_id: {task_id} and step_id: {step_id}"
                    )
                    raise NotFoundError("Step not found")
                step.status = status
                step.additional_input = additional_input
                session.commit()
                return await self.get_step(task_id, step_id)
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while updating step: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while updating step: {e}")
            raise

    async def get_artifact(self, artifact_id: str) -> Artifact:
        if self.debug_enabled:
            LOG.debug(f"Getting artifact with artifact_id: {artifact_id}")
        try:
            with Session(self.engine) as session:
                artifact_model = session.get(ArtifactModel, artifact_id)
                if artifact_model is None:
                    LOG.error(f"Artifact not found with artifact_id: {artifact_id}")
                    raise NotFoundError("Artifact not found")
                return Artifact.parse_obj(artifact_model)
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting artifact: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting artifact: {e}")
            raise

    async def list_tasks(
        self, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Task], Pagination]:
        if self.debug_enabled:
            LOG.debug("Listing tasks")
        try:
            with Session(self.engine) as session:
                tasks = (
                    session.exec(select(TaskModel).offset((page - 1) * per_page).limit(per_page)).all()
                )
                total = session.exec(select(TaskModel)).count()
                pages = math.ceil(total / per_page)
                pagination = Pagination(
                    total_items=total,
                    total_pages=pages,
                    current_page=page,
                    page_size=per_page,
                )
                return [
                    Task.parse_obj(task) for task in tasks
                ], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing tasks: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing tasks: {e}")
            raise

    async def list_steps(
        self, task_id: str, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Step], Pagination]:
        if self.debug_enabled:
            LOG.debug(f"Listing steps for task_id: {task_id}")
        try:
            with Session(self.engine) as session:
                steps = (
                    session.exec(select(StepModel).where(StepModel.task_id == task_id).offset((page - 1) * per_page).limit(per_page)).all()
                )
                total = session.exec(select(StepModel).where(StepModel.task_id == task_id)).count()
                pages = math.ceil(total / per_page)
                pagination = Pagination(
                    total_items=total,
                    total_pages=pages,
                    current_page=page,
                    page_size=per_page,
                )
                return [
                    Step.parse_obj(step) for step in steps
                ], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing steps: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing steps: {e}")
            raise

    async def list_artifacts(
        self, task_id: str, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Artifact], Pagination]:
        if self.debug_enabled:
            LOG.debug(f"Listing artifacts for task_id: {task_id}")
        try:
            with Session(self.engine) as session:
                artifacts = (
                    session.exec(select(ArtifactModel).where(ArtifactModel.task_id == task_id).offset((page - 1) * per_page).limit(per_page)).all()
                )
                total = session.exec(select(ArtifactModel).where(ArtifactModel.task_id == task_id)).count()
                pages = math.ceil(total / per_page)
                pagination = Pagination(
                    total_items=total,
                    total_pages=pages,
                    current_page=page,
                    page_size=per_page,
                )
                return [
                    Artifact.parse_obj(artifact) for artifact in artifacts
                ], pagination
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while listing artifacts: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while listing artifacts: {e}")
            raise


    # Similar methods for Step and Artifact
