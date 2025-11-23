import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from app.routers.prompt_router import router as prompt_router
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="CodeAgent API", version="1.0.0")

# 注册路由
app.include_router(prompt_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "CodeAgent API Server is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )