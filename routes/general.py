from fastapi import APIRouter, HTTPException, BackgroundTasks
import os
import uuid

from llm_client.groq_client import generate_groq_response
from llm_client.gemini_client import generate_gemini_response
from setup_venv import setup_environment as setup_venv_environment
from schemas import (
    VenvType,
    EnvSetupRequest,
    EnvSetupResponse,
    DirectoryNode,
    ProjectSourceType,
    UploadStatus,
    SubmitProjectSourceRequest,
    SubmitProjectSourceResponse,
    UploadStatusResponse,
    LLMTestRequest,
    LLMTestResponse,
    GetFileContentResponse,
)
from utils import (
    build_directory_structure,
    process_upload_background,
    upload_status,
)
from config import get_project_path

router = APIRouter(prefix="/setup", tags=["Project Management Endpoints"])


@router.get("/project-source-tree")
async def get_project_source():
    """
    Webhook endpoint that returns the project source directory structure.
    The frontend polls this endpoint to get the current project structure.
    Automatically scans the project path and respects .gitignore files.
    """
    try:
        structure = build_directory_structure(get_project_path())

        def node_to_dict(node: DirectoryNode) -> dict:
            result = {
                "name": node.name,
                "type": node.type,
                "path": node.path,
            }
            if node.children:
                result["children"] = [node_to_dict(child) for child in node.children]
            else:
                result["children"] = None
            return result

        return node_to_dict(structure)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error building directory structure: {str(e)}",
        )


@router.post("/env_setup", response_model=EnvSetupResponse)
async def setup_environment(request: EnvSetupRequest):
    """Set up the virtual environment and prepare for analysis."""
    try:
        venv_path = None

        if request.venvType == VenvType.none:
            return EnvSetupResponse(
                success=True,
                message=f"No virtual environment setup requested for {request.testType} testing",
                venv_path=None,
                test_type=request.testType,
            )

        if request.venvType == VenvType.poetry:
            return EnvSetupResponse(
                success=False,
                message="Poetry environment setup is not yet supported",
                venv_path=None,
                test_type=request.testType,
            )

        env_type = request.venvType.value
        env_name = request.venvName
        install_deps = "Yes" if request.installDependencies else "No"

        setup_venv_environment(
            env_type=env_type,
            env_name=env_name,
            python_version=None,
            install_deps=install_deps,
        )

        if env_type == "venv":
            venv_path = os.path.join(get_project_path(), env_name)
        else:
            venv_path = env_name

        setup_message = f"Environment '{env_name}' successfully created using {env_type}"
        if request.installDependencies:
            setup_message += " with dependencies installed"

        return EnvSetupResponse(
            success=True,
            message=setup_message,
            venv_path=venv_path,
            test_type=request.testType,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up environment: {str(e)}")


@router.post("/upload_project", response_model=SubmitProjectSourceResponse)
async def submit_project_source(
    request: SubmitProjectSourceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit project source endpoint.
    Starts a background task to process the upload (builds vectorstore) and returns immediately.
    """
    task_id = str(uuid.uuid4())

    upload_status[task_id] = {
        "status": UploadStatus.pending,
        "message": "Upload request received, starting processing...",
        "progress": 0,
        "path": request.path,
        "type": request.type,
    }

    background_tasks.add_task(process_upload_background, task_id, request.path, request.type)

    print("=" * 50)
    print("PROJECT SOURCE SUBMITTED")
    print("=" * 50)
    print(f"Task ID: {task_id}")
    print(f"Path: {request.path}")
    print(f"Type: {request.type.split('.')[0] if '.' in request.type else request.type}")
    print("=" * 50)

    return SubmitProjectSourceResponse(
        success=True,
        message="Upload started. Check status endpoint for progress.",
        task_id=task_id,
    )


@router.get("/upload_status/{task_id}", response_model=UploadStatusResponse)
async def get_upload_status(task_id: str):
    """
    Get the status of an upload task.
    Frontend polls this endpoint to check upload progress.
    """
    if task_id not in upload_status:
        raise HTTPException(status_code=404, detail="Task ID not found")

    status_data = upload_status[task_id]

    return UploadStatusResponse(
        status=status_data["status"],
        message=status_data["message"],
        progress=status_data.get("progress"),
        path=status_data.get("path"),
        type=status_data.get("type"),
    )


@router.get("/upload_status", response_model=UploadStatusResponse)
async def get_latest_upload_status():
    """
    Get the status of the most recent upload task.
    Convenience endpoint if you only track one upload at a time.
    """
    if not upload_status:
        raise HTTPException(status_code=404, detail="No upload tasks found")

    task_id = list(upload_status.keys())[-1]
    status_data = upload_status[task_id]

    return UploadStatusResponse(
        status=status_data["status"],
        message=status_data["message"],
        progress=status_data.get("progress"),
        path=status_data.get("path"),
        type=status_data.get("type"),
    )


@router.post("/test", response_model=LLMTestResponse)
async def test_llm(request: LLMTestRequest):
    """
    Test LLM endpoint to validate model and service provider.
    Takes model_name, provider, and prompt in the message.
    Returns success or error response with the LLM output.
    """
    try:
        if not request.model_name or not request.provider or not request.prompt or not request.api_key:
            return LLMTestResponse(
                success=False,
                message="Missing required fields",
                error="provider, model_name, api_key, and prompt are required",
            )

        provider = request.provider.lower()

        if provider == "groq":
            try:
                response_text = generate_groq_response(
                    model_name=request.model_name,
                    api_key=request.api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt,
                )

                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from {request.provider} using model {request.model_name}",
                    response=response_text,
                )
            except Exception as e:
                return LLMTestResponse(
                    success=False,
                    message="Error with Groq service",
                    error=str(e),
                )

        elif provider == "gemini":
            try:
                print("Trying with Gemini Client")
                response_text = generate_gemini_response(
                    model_name=request.model_name,
                    api_key=request.api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt,
                )

                print(response_text)

                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from Gemini using model {request.model_name}",
                    response=response_text,
                )
            except Exception as e:
                return LLMTestResponse(
                    success=False,
                    message="Error with Gemini service",
                    error=str(e),
                )

        else:
            return LLMTestResponse(
                success=False,
                message=f"Unsupported service provider: {request.provider}",
                error=f"Available providers: groq, gemini. Got: {request.provider}",
            )

    except Exception as e:
        return LLMTestResponse(
            success=False,
            message="An unexpected error occurred",
            error=str(e),
        )


@router.get("/getFileContent", response_model=GetFileContentResponse)
async def get_file_content(path: str):
    """
    Get the content of a file.
    Query parameter: path={complete_file_path}
    Returns the file content along with metadata.
    """
    try:
        if not path:
            return GetFileContentResponse(
                success=False,
                message="Missing required parameter: path",
            )

        file_path = path.strip()

        if not os.path.exists(file_path):
            return GetFileContentResponse(
                success=False,
                message=f"File not found: {file_path}",
            )

        if not os.path.isfile(file_path):
            return GetFileContentResponse(
                success=False,
                message=f"Path is a directory, not a file: {file_path}",
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception:
                return GetFileContentResponse(
                    success=False,
                    message="Error reading file: Could not decode file with utf-8 or latin-1",
                )

        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1].lstrip(".")

        from schemas import FileData

        file_data = FileData(
            name=file_name,
            path=file_path,
            content=content,
            size=file_size,
            type=file_extension if file_extension else "no extension",
        )

        return GetFileContentResponse(
            success=True,
            data=file_data,
            message="File loaded successfully",
        )

    except PermissionError:
        return GetFileContentResponse(
            success=False,
            message=f"Permission denied: Cannot read file {path}",
        )
    except Exception as e:
        return GetFileContentResponse(
            success=False,
            message=f"Error reading file: {str(e)}",
        )
