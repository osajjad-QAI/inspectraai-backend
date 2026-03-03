from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import initialize_runtime_config

initialize_runtime_config()

from routes.general import router as general_router
from routes.testing import router as testing_router
from routes.health import router as health_router

app = FastAPI(title="InspectraAI Backend API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(general_router)
app.include_router(testing_router)
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


