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
    installDependencies: bool
    path: Optional[str] = None


class EnvSetupResponse(BaseModel):
    success: bool
    message: str
    venv_path: Optional[str] = None


# ==================== Directory Structure Models ====================

class DirectoryNode(BaseModel):
    name: str
    type: str  # "file" or "folder"
    path: str
    children: Optional[List["DirectoryNode"]] = None


class ProjectSourceTreeRequest(BaseModel):
    path: Optional[str] = None


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
    source: str

    class Config:
        extra = "forbid"


class SubmitProjectSourceResponse(BaseModel):
    success: bool
    message: str
    task_id: str
    cloned_path: Optional[str] = None


class UploadStatusResponse(BaseModel):
    status: UploadStatus
    message: str
    progress: Optional[int] = None
    path: Optional[str] = None
    source: Optional[str] = None


class PreprocessProjectRequest(BaseModel):
    path: str

    class Config:
        extra = "forbid"


class PreprocessProjectResponse(BaseModel):
    success: bool
    message: str
    task_id: str


class PreprocessStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PreprocessStatusResponse(BaseModel):
    status: PreprocessStatus
    message: str
    progress: Optional[int] = None
    path: Optional[str] = None


# ==================== LLM Test Models ====================

class LLMTestRequest(BaseModel):
    provider: str
    model_name: Optional[str] = None
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


# ==================== API Key Configuration Models ====================

class APIProviderType(str, Enum):
    groq = "groq"
    gemini = "gemini"
    openai = "openai"
    kimi = "kimi"
    anthropic = "anthropic"


class APIKeySetupRequest(BaseModel):
    api_key: str
    type: APIProviderType


class APIKeySetupResponse(BaseModel):
    success: bool
    message: str
    env_variable: Optional[str] = None
    error: Optional[str] = None


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
