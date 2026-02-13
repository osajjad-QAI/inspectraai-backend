from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ==================== Environment Setup Models ====================

class VenvType(str, Enum):
    venv = "venv"
    conda = "conda"
    poetry = "poetry"
    none = "none"


class TestType(str, Enum):
    static = "static"
    dynamic = "dynamic"
    sql = "sql"


class EnvSetupRequest(BaseModel):
    venvName: str
    venvType: VenvType
    testType: TestType
    installDependencies: bool


class EnvSetupResponse(BaseModel):
    success: bool
    message: str
    venv_path: Optional[str] = None
    test_type: TestType


# ==================== Directory Structure Models ====================

class DirectoryNode(BaseModel):
    name: str
    type: str  # "file" or "folder"
    path: str
    children: Optional[List["DirectoryNode"]] = None


# ==================== Project Source Models ====================

class ProjectSourceType(str, Enum):
    github = "github"
    local = "local"


class UploadStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SubmitProjectSourceRequest(BaseModel):
    path: str
    type: ProjectSourceType


class SubmitProjectSourceResponse(BaseModel):
    success: bool
    message: str
    task_id: str


class UploadStatusResponse(BaseModel):
    status: UploadStatus
    message: str
    progress: Optional[int] = None
    path: Optional[str] = None
    type: Optional[str] = None


# ==================== LLM Test Models ====================

class LLMTestRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str
    prompt: str


class LLMTestResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None
    error: Optional[str] = None


# ==================== File Content Models ====================

class FileData(BaseModel):
    name: str
    path: str
    content: str
    size: int
    type: str


class GetFileContentRequest(BaseModel):
    file_path: str


class GetFileContentResponse(BaseModel):
    success: bool
    data: Optional[FileData] = None
    message: str


# ==================== Testing Response Models ====================

class DynamicTestingRequest(BaseModel):
    project_run_command: str
    venv_type: str
    venv_name: str
    project_path: Optional[str] = None


class DynamicTestingStatusResponse(BaseModel):
    status: str
    current_agent: Optional[str] = None
    message: Optional[str] = None
    updated_at: Optional[str] = None
    current_error: Optional[dict] = None
    last_error: Optional[dict] = None
    error_count: Optional[int] = None
    recent_errors: Optional[List[dict]] = None
    all_errors: Optional[List[dict]] = None

class TestingResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
