from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
import os
import uuid
import subprocess
import shutil
import stat
from urllib.parse import urlparse
from dotenv import set_key, load_dotenv

from llm_client.groq_client import generate_groq_response
from llm_client.gemini_client import generate_gemini_response
from utils.setup_venv import setup_environment as setup_venv_environment
from core.schemas import (
    VenvType,
    EnvSetupRequest,
    EnvSetupResponse,
    DirectoryNode,
    ProjectSourceTreeRequest,
    ProjectSourceType,
    UploadStatus,
    SubmitProjectSourceRequest,
    SubmitProjectSourceResponse,
    UploadStatusResponse,
    PreprocessProjectRequest,
    PreprocessProjectResponse,
    PreprocessStatus,
    PreprocessStatusResponse,
    LLMTestRequest,
    LLMTestResponse,
    GetFileContentResponse,
    APIKeySetupRequest,
    APIKeySetupResponse,
    APIProviderType,
)
from utils.filesystem import (
    build_directory_structure,
    process_upload_background,
    upload_status,
)
from core.build_rag import build_and_save_vectorstore
from config.runtime import get_project_path

router = APIRouter(prefix="/setup", tags=["Project Management Endpoints"])

# Global preprocess status tracker
preprocess_status: dict[str, dict] = {}


def _remove_readonly(func, path, excinfo):
    """Error handler for shutil.rmtree to remove read-only files on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _infer_repo_name(repo_url: str) -> str:
    """Infer a safe local folder name from a GitHub repo URL."""
    parsed = urlparse(repo_url)
    repo_name = os.path.basename(parsed.path.rstrip("/"))
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    return repo_name or "repo"


def _clone_github_repo(repo_url: str) -> str:
    """Clone a GitHub repository and return the absolute clone path."""
    clone_root = r"C:\\Inspectra\\cloned_projects"
    os.makedirs(clone_root, exist_ok=True)

    repo_name = _infer_repo_name(repo_url)
    target_dir = os.path.join(clone_root, repo_name)

    # If repo folder already exists, remove it and clone a fresh copy.
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir, onerror=_remove_readonly)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to delete existing repository folder: {str(e)}")

    result = subprocess.run(
        ["git", "clone", repo_url, target_dir],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        error_output = stderr or stdout or "Unknown git clone error"
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {error_output}")

    return os.path.abspath(target_dir)


def _resolve_llm_settings(provider: str, model_name: str | None) -> tuple[str, str]:
    """Resolve provider-specific API key and model from .env (with request model fallback)."""
    provider_key_var_map = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }

    provider_model_var_candidates = {
        "groq": ["GROQ_MODEL_NAME", "GROQ_MODEL", "MODEL_NAME"],
        "gemini": ["GEMINI_MODEL_NAME", "GEMINI_MODEL", "MODEL_NAME"],
    }

    env_file_path = os.path.join(os.getcwd(), ".env")
    load_dotenv(env_file_path, override=True)

    api_var = provider_key_var_map.get(provider, "")
    resolved_api_key = os.getenv(api_var, "").strip() if api_var else ""

    resolved_model_name = (model_name or "").strip()
    if not resolved_model_name:
        for env_var in provider_model_var_candidates.get(provider, ["MODEL_NAME"]):
            value = os.getenv(env_var, "").strip()
            if value:
                resolved_model_name = value
                break

    return resolved_api_key, resolved_model_name


@router.post("/project-source-tree")
async def get_project_source(request: ProjectSourceTreeRequest):
    """
    Webhook endpoint that returns the project source directory structure.
    The frontend polls this endpoint to get the current project structure.
    Automatically scans the project path and respects .gitignore files.
    
    Request Body:
        path (optional): Project path to scan. If not provided, uses configured PROJECT_PATH.
    """
    try:
        project_path = request.path.strip() if request.path else get_project_path()
        
        if not os.path.isdir(project_path):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid directory path: {project_path}"
            )
        
        structure = build_directory_structure(project_path)

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


@router.get("/current-path")
async def get_current_path():
    """
    Get the current configured project path.
    Returns the path that project-source-tree API uses by default.
    """
    try:
        current_path = get_project_path()
        return {
            "success": True,
            "path": current_path,
            "message": "Current project path retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving current path: {str(e)}",
        )


@router.post("/env_setup", response_model=EnvSetupResponse)
async def setup_environment(request: EnvSetupRequest):
    """Set up the virtual environment and prepare for analysis."""
    try:
        venv_path = None
        project_path = request.path.strip() if request.path else get_project_path()

        if request.venvType == VenvType.none:
            return EnvSetupResponse(
                success=True,
                message="No virtual environment setup requested",
                venv_path=None,
            )

        if request.venvType == VenvType.poetry:
            return EnvSetupResponse(
                success=False,
                message="Poetry environment setup is not yet supported",
                venv_path=None,
            )

        env_type = request.venvType.value
        env_name = request.venvName
        install_deps = "Yes" if request.installDependencies else "No"

        if env_type == VenvType.venv.value and not os.path.isdir(project_path):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid project path for venv setup: {project_path}",
            )

        setup_venv_environment(
            env_type=env_type,
            env_name=env_name,
            python_version=None,
            install_deps=install_deps,
            project_path=project_path,
        )

        if env_type == "venv":
            venv_path = os.path.join(project_path, env_name)
        else:
            venv_path = env_name

        setup_message = f"Environment '{env_name}' successfully created using {env_type}"
        if request.installDependencies:
            setup_message += " with dependencies installed"

        return EnvSetupResponse(
            success=True,
            message=setup_message,
            venv_path=venv_path,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up environment: {str(e)}")


@router.post("/handle_github", response_model=SubmitProjectSourceResponse)
async def submit_project_source(
    raw_request: Request,
    request: SubmitProjectSourceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit project source endpoint.
    Starts a background task to process the upload (builds vectorstore) and returns immediately.
    """
    body = await raw_request.json()
    allowed_keys = {"source", "path"}
    unexpected_keys = set(body.keys()) - allowed_keys
    if unexpected_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported fields in request body: {', '.join(sorted(unexpected_keys))}",
        )

    task_id = str(uuid.uuid4())
    source_value = request.source.strip().lower()
    if source_value not in (ProjectSourceType.github.value, ProjectSourceType.local.value):
        raise HTTPException(status_code=400, detail="source must be 'github' or 'local'")

    effective_path = request.path
    cloned_path = None

    if source_value == ProjectSourceType.github.value:
        if not request.path.strip():
            raise HTTPException(status_code=400, detail="GitHub repository URL is required in 'path'")
        cloned_path = _clone_github_repo(request.path.strip())
        effective_path = cloned_path
    else:
        if not os.path.isdir(request.path):
            raise HTTPException(status_code=400, detail=f"Invalid local path: {request.path}")
        effective_path = os.path.abspath(request.path)

    upload_status[task_id] = {
        "status": UploadStatus.pending,
        "message": "Upload request received, starting processing...",
        "progress": 0,
        "path": effective_path,
        "source": source_value,
    }

    # background_tasks.add_task(process_upload_background, task_id, effective_path, source_value)

    print("=" * 50)
    print("PROJECT SOURCE SUBMITTED")
    print("=" * 50)
    print(f"Task ID: {task_id}")
    print(f"Path: {effective_path}")
    print(f"Source: {source_value}")
    print("=" * 50)

    return SubmitProjectSourceResponse(
        success=True,
        message="Upload started. Check status endpoint for progress.",
        task_id=task_id,
        cloned_path=cloned_path,
    )


async def _process_preprocess_background(task_id: str, path: str):
    """Background task to preprocess project and build vector store."""
    try:
        preprocess_status[task_id].update({
            "status": PreprocessStatus.processing,
            "message": "Building vector store...",
            "progress": 50,
        })

        # Run preprocessing in thread pool to avoid blocking
        import concurrent.futures
        import asyncio
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, build_and_save_vectorstore, path)

        preprocess_status[task_id] = {
            "status": PreprocessStatus.completed,
            "message": "Vector store built successfully",
            "progress": 100,
            "path": path,
        }

        print("=" * 50)
        print("PREPROCESSING COMPLETED")
        print("=" * 50)
        print(f"Task ID: {task_id}")
        print(f"Path: {path}")
        print("=" * 50)

    except Exception as e:
        preprocess_status[task_id] = {
            "status": PreprocessStatus.failed,
            "message": f"Error during preprocessing: {str(e)}",
            "progress": 0,
            "path": path,
        }
        print(f"Error preprocessing {task_id}: {str(e)}")


@router.post("/preprocess-project", response_model=PreprocessProjectResponse)
async def preprocess_project(
    request: PreprocessProjectRequest,
    background_tasks: BackgroundTasks,
):
    """
    Preprocess project by building vector store.
    Takes project path and creates FAISS vector store from code files.
    """
    try:
        project_path = request.path.strip()

        if not os.path.isdir(project_path):
            raise HTTPException(status_code=400, detail=f"Invalid project path: {project_path}")

        task_id = str(uuid.uuid4())

        preprocess_status[task_id] = {
            "status": PreprocessStatus.pending,
            "message": "Preprocessing request received, starting...",
            "progress": 10,
            "path": project_path,
        }

        background_tasks.add_task(_process_preprocess_background, task_id, project_path)

        print("=" * 50)
        print("PREPROCESSING STARTED")
        print("=" * 50)
        print(f"Task ID: {task_id}")
        print(f"Path: {project_path}")
        print("=" * 50)

        return PreprocessProjectResponse(
            success=True,
            message="Preprocessing started. Check status endpoint for progress.",
            task_id=task_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting preprocessing: {str(e)}")


@router.get("/preprocess-status", response_model=PreprocessStatusResponse)
async def get_preprocess_status():
    """
    Get the status of the most recent preprocessing task.
    Returns real-time status of vector store building process.
    """
    if not preprocess_status:
        raise HTTPException(status_code=404, detail="No preprocessing tasks found")

    task_id = list(preprocess_status.keys())[-1]
    status_data = preprocess_status[task_id]

    return PreprocessStatusResponse(
        status=status_data["status"],
        message=status_data["message"],
        progress=status_data.get("progress"),
        path=status_data.get("path"),
    )


@router.post("/test", response_model=LLMTestResponse)
async def test_llm(request: LLMTestRequest):
    """
    Test LLM endpoint to validate model and service provider.
    Takes provider and prompt, with optional model_name in the message.
    API key is always loaded from .env based on provider.
    Returns success or error response with the LLM output.
    """
    try:
        if not request.provider or not request.prompt:
            return LLMTestResponse(
                success=False,
                message="Missing required fields",
                error="provider and prompt are required",
            )

        provider = request.provider.strip().lower()
        api_key, model_name = _resolve_llm_settings(provider, request.model_name)

        if not api_key:
            return LLMTestResponse(
                success=False,
                message="Missing API key",
                error=f"No API key found in .env for provider '{provider}'",
            )

        if not model_name:
            return LLMTestResponse(
                success=False,
                message="Missing model name",
                error=f"No model_name found for provider '{provider}' in request or .env",
            )

        if provider == "groq":
            try:
                response_text = generate_groq_response(
                    model_name=model_name,
                    api_key=api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt,
                )

                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from {request.provider} using model {model_name}",
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
                    model_name=model_name,
                    api_key=api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt,
                )

                print(response_text)

                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from Gemini using model {model_name}",
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


@router.post("/api-key", response_model=APIKeySetupResponse)
async def setup_api_key(request: APIKeySetupRequest):
    """
    Set up API key for different LLM providers.
    Takes the API key and provider type (groq, gemini, openai, kimi, anthropic).
    Stores the API key in the .env file with the appropriate environment variable name.
    
    Provider to Environment Variable Mapping:
    - groq → GROQ_API_KEY
    - gemini → GEMINI_API_KEY
    - openai → OPENAI_API_KEY
    - kimi → KIMI_API_KEY
    - anthropic → ANTHROPIC_API_KEY
    """
    try:
        # Validate API key is not empty
        if not request.api_key or not request.api_key.strip():
            return APIKeySetupResponse(
                success=False,
                message="API key cannot be empty",
                error="Please provide a valid API key",
            )
        
        # Mapping of provider types to environment variable names
        provider_to_env_var = {
            APIProviderType.groq: "GROQ_API_KEY",
            APIProviderType.gemini: "GEMINI_API_KEY",
            APIProviderType.openai: "OPENAI_API_KEY",
            APIProviderType.kimi: "KIMI_API_KEY",
            APIProviderType.anthropic: "ANTHROPIC_API_KEY",
        }
        
        # Get the environment variable name for the provider
        env_var_name = provider_to_env_var.get(request.type)
        if not env_var_name:
            return APIKeySetupResponse(
                success=False,
                message=f"Unsupported provider type: {request.type}",
                error=f"Supported providers: {', '.join([p.value for p in APIProviderType])}",
            )
        
        # Get the .env file path (in the current working directory)
        env_file_path = os.path.join(os.getcwd(), ".env")
        
        # Set the API key in the .env file
        try:
            set_key(env_file_path, env_var_name, request.api_key, quote_mode="never")
            # Also set it in the current environment for immediate use
            os.environ[env_var_name] = request.api_key
            
            return APIKeySetupResponse(
                success=True,
                message=f"API key for {request.type.value} successfully configured",
                env_variable=env_var_name,
            )
        except Exception as e:
            return APIKeySetupResponse(
                success=False,
                message=f"Error writing to .env file: {str(e)}",
                error=str(e),
            )
        
    except Exception as e:
        return APIKeySetupResponse(
            success=False,
            message="An unexpected error occurred while setting up API key",
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

        from core.schemas import FileData

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
