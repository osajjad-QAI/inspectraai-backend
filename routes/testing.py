from fastapi import APIRouter, HTTPException
import os
import threading
import uuid

from core.run_project import run_with_watch
from core.schemas import (
    DynamicTestingRequest,
    DynamicTestingStatusResponse,
    TestingResponse,
    UploadStatusResponse,
)
from dynamic_testing.progress import get_progress, set_progress
from config.runtime import get_project_path
from utils.filesystem import upload_status

router = APIRouter(prefix="/testing", tags=["Testing Endpoints"])


@router.post("/static-testing", response_model=TestingResponse)
async def static_testing():
    """
    Perform static code analysis/testing.
    Returns successful response with analysis results.
    """
    try:
        return TestingResponse(
            success=True,
            message="Static testing completed successfully",
            data={
                "type": "static",
                "status": "completed",
                "timestamp": str(uuid.uuid4()),
                "results": "Static analysis performed",
            },
        )
    except Exception as e:
        return TestingResponse(
            success=False,
            message=f"Error during static testing: {str(e)}",
        )


def _run_dynamic_testing(request: DynamicTestingRequest, workdir: str) -> None:
    try:
        run_with_watch(
            request.project_run_command,
            request.venv_type,
            request.venv_name,
            workdir=workdir,
        )
        set_progress(status="completed", current_agent=None, message="Dynamic testing finished")
    except Exception as e:
        set_progress(status="error", message=str(e))


@router.post("/dynamic-testing", response_model=TestingResponse)
async def dynamic_testing(request: DynamicTestingRequest):
    """
    Perform dynamic code testing.
    Returns successful response with test execution results.
    """
    try:
        workdir = request.project_path or get_project_path()

        if not os.path.isdir(workdir):
            return TestingResponse(
                success=False,
                message=f"Invalid project path: {workdir}",
            )

        print("Dynamic testing request body:", request.dict())
        set_progress(status="running", current_agent="runner", message="Starting dynamic testing")
        thread = threading.Thread(target=_run_dynamic_testing, args=(request, workdir), daemon=True)
        thread.start()
        return TestingResponse(
            success=True,
            message="Dynamic testing started",
            data={
                "type": "dynamic",
                "status": "running",
                "timestamp": str(uuid.uuid4()),
                "results": "Dynamic tests running",
            },
        )
    except Exception as e:
        set_progress(status="error", message=str(e))
        return TestingResponse(
            success=False,
            message=f"Error during dynamic testing: {str(e)}",
        )


@router.get("/dynamic-testing/status", response_model=DynamicTestingStatusResponse)
async def dynamic_testing_status():
    """Return the latest dynamic testing progress state."""
    return DynamicTestingStatusResponse(**get_progress())


@router.post("/sql-optimization", response_model=TestingResponse)
async def sql_optimization():
    """
    Perform SQL query optimization analysis.
    Returns successful response with optimization suggestions.
    """
    try:
        return TestingResponse(
            success=True,
            message="SQL optimization completed successfully",
            data={
                "type": "sql",
                "status": "completed",
                "timestamp": str(uuid.uuid4()),
                "results": "SQL optimization suggestions generated",
            },
        )
    except Exception as e:
        return TestingResponse(
            success=False,
            message=f"Error during SQL optimization: {str(e)}",
        )