from pathlib import Path

from agent_protocol.agent import base_router
from fastapi.responses import FileResponse
from fastapi import (
    HTTPException as FastAPIHTTPException,  # Import HTTPException from FastAPI
)
from agbenchmark.app import get_artifact
from agbenchmark.app import get_skill_tree
from fastapi import APIRouter

def add_benchmark_routes():

    new_router = APIRouter()

    @new_router.get("/skill_tree")
    async def get_skill_tree_endpoint() -> dict:  # Renamed to avoid a clash with the function import
        return get_skill_tree()

    @new_router.get("/agent/challenges/{challenge_id}/artifacts/{artifact_id}")
    async def get_artifact_endpoint(
        challenge_id: str, artifact_id: str
    ) -> FileResponse:  # Added return type annotation
        return get_artifact(challenge_id, artifact_id)

    # Include the new router in the base router
    base_router.include_router(new_router)

    return base_router
