from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import uvicorn
import threading
from llm_client.groq_client import generate_groq_response
from llm_client.gemini_client import generate_gemini_response
from run_project import run_with_watch
from schemas import (
    VenvType,
    TestType,
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
    DynamicTestingRequest,
    DynamicTestingStatusResponse,
    TestingResponse,
)
from dynamic_testing.progress import get_progress, set_progress
from utils import (
    build_directory_structure,
    process_upload_background,
    upload_status,
)

app = FastAPI(title="InspectraAI Backend API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Configuration ====================
# Set your project path here or via environment variable
PROJECT_PATH = os.getenv("PROJECT_PATH", "E:/Quanticept/opentendrAll/openTendr")  # Change this to your project path

# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "InspectraAI Backend API is running",
        "version": "1.0.0"
    }

@app.get("/project-source")
async def get_project_source():
    """
    Webhook endpoint that returns the project source directory structure.
    The frontend polls this endpoint to get the current project structure.
    Automatically scans the project path and respects .gitignore files.
    """
    try:
        # Build directory structure from configured project path
        structure = build_directory_structure(PROJECT_PATH)
        
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
            detail=f"Error building directory structure: {str(e)}"
        )

@app.post("/env_setup", response_model=EnvSetupResponse)
async def setup_environment(request: EnvSetupRequest):
    """Set up the virtual environment and prepare for analysis."""
    try:
        venv_path = None
        if request.venvType != VenvType.none:
            venv_path = f"./{request.venvName}"
        
        setup_message = f"Environment setup initiated: {request.venvType} environment"
        if request.installDependencies:
            setup_message += " with dependencies"
        setup_message += f" for {request.testType} testing"
        
        return EnvSetupResponse(
            success=True,
            message=setup_message,
            venv_path=venv_path,
            test_type=request.testType
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up environment: {str(e)}")

@app.post("/upload_project", response_model=SubmitProjectSourceResponse)
async def submit_project_source(
    request: SubmitProjectSourceRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit project source endpoint.
    Starts a background task to process the upload (builds vectorstore) and returns immediately.
    """
    task_id = str(uuid.uuid4())
    
    # Initialize status as pending
    upload_status[task_id] = {
        "status": UploadStatus.pending,
        "message": "Upload request received, starting processing...",
        "progress": 0,
        "path": request.path,
        "type": request.type
    }
    
    # Start background task
    background_tasks.add_task(process_upload_background, task_id, request.path, request.type)
    
    # Print the received data
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
        task_id=task_id
    )

@app.get("/upload_status/{task_id}", response_model=UploadStatusResponse)
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
        type=status_data.get("type")
    )

@app.get("/upload_status", response_model=UploadStatusResponse)
async def get_latest_upload_status():
    """
    Get the status of the most recent upload task.
    Convenience endpoint if you only track one upload at a time.
    """
    if not upload_status:
        raise HTTPException(status_code=404, detail="No upload tasks found")
    
    # Get the most recent task (last one in dict)
    task_id = list(upload_status.keys())[-1]
    status_data = upload_status[task_id]
    
    return UploadStatusResponse(
        status=status_data["status"],
        message=status_data["message"],
        progress=status_data.get("progress"),
        path=status_data.get("path"),
        type=status_data.get("type")
    )

@app.post("/test", response_model=LLMTestResponse)
async def test_llm(request: LLMTestRequest):
    """
    Test LLM endpoint to validate model and service provider.
    Takes model_name, provider, and prompt in the message.
    Returns success or error response with the LLM output.
    """
    try:
        # Validate input
        if not request.model_name or not request.provider or not request.prompt or not request.api_key:
            return LLMTestResponse(
                success=False,
                message="Missing required fields",
                error="provider, model_name, api_key, and prompt are required"
            )
        
        provider = request.provider.lower()
        
        # Handle different service providers
        if provider == "groq":
            try:
                response_text = generate_groq_response(
                    model_name=request.model_name,
                    api_key=request.api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt
                )
                
                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from {request.provider} using model {request.model_name}",
                    response=response_text
                )
            except Exception as e:
                return LLMTestResponse(
                    success=False,
                    message=f"Error with Groq service",
                    error=str(e)
                )
        
        elif provider == "gemini":
            try:
                print("Trying with Gemini Client")
                response_text = generate_gemini_response(
                    model_name=request.model_name,
                    api_key=request.api_key,
                    system_prompt="You are a helpful assistant.",
                    user_prompt=request.prompt
                )

                print(response_text)
                
                return LLMTestResponse(
                    success=True,
                    message=f"Successfully received response from Gemini using model {request.model_name}",
                    response=response_text
                )
            except Exception as e:
                return LLMTestResponse(
                    success=False,
                    message=f"Error with Gemini service",
                    error=str(e)
                )
        
        else:
            return LLMTestResponse(
                success=False,
                message=f"Unsupported service provider: {request.provider}",
                error=f"Available providers: groq, gemini. Got: {request.provider}"
            )
    
    except Exception as e:
        return LLMTestResponse(
            success=False,
            message="An unexpected error occurred",
            error=str(e)
        )

@app.get("/getFileData", response_model=GetFileContentResponse)
async def get_file_content(path: str):
    """
    Get the content of a file.
    Query parameter: path={complete_file_path}
    Returns the file content along with metadata.
    """
    try:
        # Validate input
        if not path:
            return GetFileContentResponse(
                success=False,
                message="Missing required parameter: path"
            )
        
        # Normalize the path
        file_path = path.strip()
        
        # Check if file exists
        if not os.path.exists(file_path):
            return GetFileContentResponse(
                success=False,
                message=f"File not found: {file_path}"
            )
        
        # Check if path is a file (not a directory)
        if not os.path.isfile(file_path):
            return GetFileContentResponse(
                success=False,
                message=f"Path is a directory, not a file: {file_path}"
            )
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                return GetFileContentResponse(
                    success=False,
                    message=f"Error reading file: Could not decode file with utf-8 or latin-1"
                )
        
        # Get file metadata
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        
        # Extract filename and extension
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1].lstrip('.')
        
        # Create response data
        from schemas import FileData
        file_data = FileData(
            name=file_name,
            path=file_path,
            content=content,
            size=file_size,
            type=file_extension if file_extension else "no extension"
        )
        
        return GetFileContentResponse(
            success=True,
            data=file_data,
            message="File loaded successfully"
        )
        
    except PermissionError:
        return GetFileContentResponse(
            success=False,
            message=f"Permission denied: Cannot read file {path}"
        )
    except Exception as e:
        return GetFileContentResponse(
            success=False,
            message=f"Error reading file: {str(e)}"
        )

@app.post("/static-testing", response_model=TestingResponse)
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
                "results": "Static analysis performed"
            }
        )
    except Exception as e:
        return TestingResponse(
            success=False,
            message=f"Error during static testing: {str(e)}"
        )

def _run_dynamic_testing(request: DynamicTestingRequest, workdir: str) -> None:
    try:
        run_with_watch(
            request.project_run_command,
            request.venv_type,
            request.venv_name,
            workdir=workdir
        )
        set_progress(status="completed", current_agent=None, message="Dynamic testing finished")
    except Exception as e:
        set_progress(status="error", message=str(e))


@app.post("/dynamic-testing", response_model=TestingResponse)
async def dynamic_testing(request: DynamicTestingRequest):
    """
    Perform dynamic code testing.
    Returns successful response with test execution results.
    """
    try:
        workdir = request.project_path or PROJECT_PATH

        if not os.path.isdir(workdir):
            return TestingResponse(
                success=False,
                message=f"Invalid project path: {workdir}"
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
                "results": "Dynamic tests running"
            }
        )
    except Exception as e:
        set_progress(status="error", message=str(e))
        return TestingResponse(
            success=False,
            message=f"Error during dynamic testing: {str(e)}"
        )


@app.get("/dynamic-testing/status", response_model=DynamicTestingStatusResponse)
async def dynamic_testing_status():
    """Return the latest dynamic testing progress state."""
    return DynamicTestingStatusResponse(**get_progress())

@app.post("/sql-optimization", response_model=TestingResponse)
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
                "results": "SQL optimization suggestions generated"
            }
        )
    except Exception as e:
        return TestingResponse(
            success=False,
            message=f"Error during SQL optimization: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


