# InspectraAI Backend API Documentation

## Base URL
- Local base URL: `http://127.0.0.1:8000`
- Health endpoint: `GET /`
- Interactive docs (FastAPI default):
  - Swagger UI: `http://127.0.0.1:8000/docs`
  - ReDoc: `http://127.0.0.1:8000/redoc`

## Common Notes
- Content type for POST requests: `application/json`
- Standard FastAPI validation errors return HTTP `422`.
- Some server-side exceptions return HTTP `500` as:
  - `{ "detail": "<error message>" }`

## Enums

### `VenvType`
- `venv`
- `conda`
- `poetry`
- `none`

### `ProjectSourceType`
- `github`
- `local`

### `PreprocessStatus`
- `pending`
- `processing`
- `completed`
- `failed`

### `APIProviderType`
- `groq`
- `gemini`
- `openai`
- `kimi`
- `anthropic`

---

## 1) Health Endpoint

### `GET /`
Health check endpoint.

#### Request Body
- None

#### Response (200)
```json
{
  "status": "ok",
  "message": "InspectraAI Backend API is running",
  "version": "1.0.0"
}
```

---

## 2) Setup Endpoints (`/setup`)

### `POST /setup/project-source-tree`
Returns project directory tree.

#### Request Schema
```json
{
  "path": "string (optional)"
}
```

#### Response (200)
Recursive directory node object:
```json
{
  "name": "string",
  "type": "file | folder",
  "path": "string",
  "children": [
    {
      "name": "string",
      "type": "file | folder",
      "path": "string",
      "children": null
    }
  ]
}
```

#### Error Responses
- `400`: invalid directory path
- `500`: directory structure build failure

---

### `GET /setup/current-path`
Returns current configured project path.

#### Request Body
- None

#### Response (200)
```json
{
  "success": true,
  "path": "string",
  "message": "Current project path retrieved successfully"
}
```

#### Error Responses
- `500`: could not read path

---

### `POST /setup/env_setup`
Creates/configures environment (`venv`/`conda`), optionally installs dependencies.

#### Request Schema (`EnvSetupRequest`)
```json
{
  "venvName": "string",
  "venvType": "venv | conda | poetry | none",
  "installDependencies": true,
  "path": "string (optional, used for venv target project path)"
}
```

#### Response Schema (`EnvSetupResponse`)
```json
{
  "success": true,
  "message": "string",
  "venv_path": "string | null"
}
```

#### Notes
- If `venvType = "none"`, no environment is created.
- If `venvType = "poetry"`, API currently returns unsupported message.
- For `venv`, if `path` is provided, environment path resolves as: `path/venvName`.

#### Error Responses
- `400`: invalid project path for `venv`
- `500`: setup failed

---

### `POST /setup/handle_github`
Accepts project source (`github` or `local`) and initializes upload status.

#### Request Schema (`SubmitProjectSourceRequest`)
```json
{
  "path": "string",
  "source": "github | local"
}
```

#### Response Schema (`SubmitProjectSourceResponse`)
```json
{
  "success": true,
  "message": "string",
  "task_id": "string",
  "cloned_path": "string | null"
}
```

#### Behavior
- `source = "github"`: `path` must be a GitHub repo URL, backend clones to local folder.
- `source = "local"`: `path` must be an existing local directory.

#### Error Responses
- `400`: invalid payload fields, unsupported source, invalid path, clone errors

---

### `POST /setup/preprocess-project`
Starts background preprocessing to build vector store.

#### Request Schema (`PreprocessProjectRequest`)
```json
{
  "path": "string"
}
```

#### Response Schema (`PreprocessProjectResponse`)
```json
{
  "success": true,
  "message": "string",
  "task_id": "string"
}
```

#### Error Responses
- `400`: invalid project path
- `500`: failed to start preprocessing

---

### `GET /setup/preprocess-status`
Returns most recent preprocess task status.

#### Request Body
- None

#### Response Schema (`PreprocessStatusResponse`)
```json
{
  "status": "pending | processing | completed | failed",
  "message": "string",
  "progress": 0,
  "path": "string | null"
}
```

#### Error Responses
- `404`: no preprocess task found

---

### `POST /setup/test`
Tests configured LLM provider/model using a prompt.

#### Request Schema (`LLMTestRequest`)
```json
{
  "provider": "string",
  "model_name": "string (optional)",
  "prompt": "string"
}
```

#### Response Schema (`LLMTestResponse`)
```json
{
  "success": true,
  "message": "string",
  "response": "string | null",
  "error": "string | null"
}
```

#### Notes
- Supported providers in current implementation: `groq`, `gemini`.
- API key is loaded from `.env` based on provider.

---

### `POST /setup/api-key`
Stores provider API key in `.env`.

#### Request Schema (`APIKeySetupRequest`)
```json
{
  "api_key": "string",
  "type": "groq | gemini | openai | kimi | anthropic"
}
```

#### Response Schema (`APIKeySetupResponse`)
```json
{
  "success": true,
  "message": "string",
  "env_variable": "string | null",
  "error": "string | null"
}
```

#### Environment Variable Mapping
- `groq` -> `GROQ_API_KEY`
- `gemini` -> `GEMINI_API_KEY`
- `openai` -> `OPENAI_API_KEY`
- `kimi` -> `KIMI_API_KEY`
- `anthropic` -> `ANTHROPIC_API_KEY`

---

### `GET /setup/api-key`
Returns all API key entries discovered in `.env` with metadata.

#### Request Body
- None

#### Response Schema (`APIKeyListResponse`)
```json
{
  "success": true,
  "message": "API keys metadata fetched successfully",
  "count": 2,
  "keys": [
    {
      "provider": "groq",
      "env_variable": "GROQ_API_KEY",
      "is_configured": true,
      "value_length": 51,
      "masked_value": "gsk_...UNGs"
    }
  ]
}
```

#### Notes
- Includes every `.env` variable ending with `_API_KEY`.
- Returns masked values only (not full key text).
- Empty values are returned as `is_configured: false`.

---

### `GET /setup/getFileContent`
Reads file content from query parameter path.

#### Query Params
- `path` (required): absolute or valid file path string

#### Response Schema (`GetFileContentResponse`)
```json
{
  "success": true,
  "data": {
    "name": "string",
    "path": "string",
    "content": "string",
    "size": 123,
    "type": "string"
  },
  "message": "string"
}
```

#### Error Responses
- Returns `success: false` with message for missing path, file not found, decode errors, permission errors

---

## 3) Testing Endpoints (`/testing`)

### `POST /testing/static-testing`
Runs static testing placeholder logic.

#### Request Body
- None

#### Response Schema (`TestingResponse`)
```json
{
  "success": true,
  "message": "string",
  "data": {
    "type": "static",
    "status": "completed",
    "timestamp": "string",
    "results": "string"
  }
}
```

---

### `POST /testing/dynamic-testing`
Starts dynamic testing in background thread.

#### Request Schema (`DynamicTestingRequest`)
```json
{
  "project_run_command": "string",
  "venv_type": "string",
  "venv_name": "string",
  "project_path": "string (optional)"
}
```

#### Response Schema (`TestingResponse`)
```json
{
  "success": true,
  "message": "Dynamic testing started",
  "data": {
    "type": "dynamic",
    "status": "running",
    "timestamp": "string",
    "results": "Dynamic tests running"
  }
}
```

#### Error Cases
- Returns `success: false` with message if path invalid or runtime exception occurs.

---

### `GET /testing/dynamic-testing/status`
Returns latest dynamic testing progress.

#### Request Body
- None

#### Response Schema (`DynamicTestingStatusResponse`)
```json
{
  "status": "string",
  "current_agent": "string | null",
  "message": "string | null",
  "updated_at": "string | null",
  "current_error": {},
  "last_error": {},
  "error_count": 0,
  "recent_errors": [],
  "all_errors": []
}
```

---

### `GET /testing/user-approval/status`
Returns current approval state when pipeline asks user to continue or stop.

#### Request Body
- None

#### Response Schema (`UserApprovalStatusResponse`)
```json
{
  "status": "idle | pending | resolved",
  "question": "string | null",
  "decision": "yes | no | null",
  "source": "terminal | ui | null",
  "updated_at": "string | null",
  "message": "string | null"
}
```

---

### `POST /testing/user-approval`
Submits UI decision for pending approval prompt.

#### Request Schema (`UserApprovalDecisionRequest`)
```json
{
  "decision": "yes | no"
}
```

#### Response Schema (`UserApprovalDecisionResponse`)
```json
{
  "success": true,
  "message": "Decision stored",
  "status": "resolved",
  "decision": "yes",
  "source": "ui"
}
```

---

### `POST /testing/sql-optimization`
Runs SQL optimization placeholder logic.

#### Request Body
- None

#### Response Schema (`TestingResponse`)
```json
{
  "success": true,
  "message": "string",
  "data": {
    "type": "sql",
    "status": "completed",
    "timestamp": "string",
    "results": "string"
  }
}
```

---

## 4) Consolidated Schema Definitions

### `EnvSetupRequest`
```json
{
  "venvName": "string",
  "venvType": "venv | conda | poetry | none",
  "installDependencies": "boolean",
  "path": "string | null"
}
```

### `EnvSetupResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "venv_path": "string | null"
}
```

### `SubmitProjectSourceRequest`
```json
{
  "path": "string",
  "source": "string"
}
```

### `SubmitProjectSourceResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "task_id": "string",
  "cloned_path": "string | null"
}
```

### `PreprocessProjectRequest`
```json
{
  "path": "string"
}
```

### `PreprocessProjectResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "task_id": "string"
}
```

### `PreprocessStatusResponse`
```json
{
  "status": "pending | processing | completed | failed",
  "message": "string",
  "progress": "integer | null",
  "path": "string | null"
}
```

### `LLMTestRequest`
```json
{
  "provider": "string",
  "model_name": "string | null",
  "prompt": "string"
}
```

### `LLMTestResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "response": "string | null",
  "error": "string | null"
}
```

### `APIKeySetupRequest`
```json
{
  "api_key": "string",
  "type": "groq | gemini | openai | kimi | anthropic"
}
```

### `APIKeySetupResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "env_variable": "string | null",
  "error": "string | null"
}
```

### `FileData`
```json
{
  "name": "string",
  "path": "string",
  "content": "string",
  "size": "integer",
  "type": "string"
}
```

### `GetFileContentResponse`
```json
{
  "success": "boolean",
  "data": "FileData | null",
  "message": "string"
}
```

### `DynamicTestingRequest`
```json
{
  "project_run_command": "string",
  "venv_type": "string",
  "venv_name": "string",
  "project_path": "string | null"
}
```

### `DynamicTestingStatusResponse`
```json
{
  "status": "string",
  "current_agent": "string | null",
  "message": "string | null",
  "updated_at": "string | null",
  "current_error": "object | null",
  "last_error": "object | null",
  "error_count": "integer | null",
  "recent_errors": "array<object> | null",
  "all_errors": "array<object> | null"
}
```

### `TestingResponse`
```json
{
  "success": "boolean",
  "message": "string",
  "data": "object | null"
}
```
