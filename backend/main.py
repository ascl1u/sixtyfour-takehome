import os
import asyncio
from typing import Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import aiofiles

from engine import get_engine, WorkflowStatus, BlockStatus
from blocks import BlockType


# Data directory for file storage
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown - cleanup


app = FastAPI(
    title="Workflow Engine API",
    description="API for executing data enrichment workflows",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class BlockDefinition(BaseModel):
    id: str
    type: str  # BlockType value
    config: dict[str, Any] = {}


class WorkflowRequest(BaseModel):
    blocks: list[BlockDefinition]


class BlockProgressResponse(BaseModel):
    block_id: str
    block_type: str
    status: str
    progress: int
    error: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    blocks: list[BlockProgressResponse]
    current_block_index: int
    error: Optional[str] = None
    result_preview: Optional[list[dict]] = None
    result_columns: Optional[list[str]] = None
    result_row_count: int = 0


class WorkflowCreateResponse(BaseModel):
    workflow_id: str
    message: str


class FileListResponse(BaseModel):
    files: list[str]


# API Routes
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Workflow Engine API"}


@app.get("/blocks")
async def get_block_types():
    """Get available block types and their configurations."""
    return {
        "blocks": [
            {
                "type": BlockType.READ_CSV.value,
                "name": "Read CSV",
                "description": "Load a CSV file into the workflow",
                "color": "#8B5CF6",  # Purple
                "config_schema": {
                    "file_path": {"type": "string", "required": True, "description": "Path to CSV file"}
                },
            },
            {
                "type": BlockType.ENRICH_LEAD.value,
                "name": "Enrich Lead",
                "description": "Enrich lead information using Sixtyfour API",
                "color": "#3B82F6",  # Blue
                "config_schema": {
                    "struct": {"type": "array", "required": False, "description": "Fields to enrich"},
                    "name_column": {"type": "string", "default": "name"},
                    "company_column": {"type": "string", "default": "company"},
                    "linkedin_column": {"type": "string", "default": "linkedin"},
                },
            },
            {
                "type": BlockType.FIND_EMAIL.value,
                "name": "Find Email",
                "description": "Find email addresses for leads",
                "color": "#F97316",  # Orange
                "config_schema": {
                    "mode": {"type": "string", "default": "PROFESSIONAL"},
                    "output_column": {"type": "string", "default": "found_email"},
                    "skip_existing": {"type": "boolean", "default": True},
                },
            },
            {
                "type": BlockType.FILTER.value,
                "name": "Filter",
                "description": "Filter rows based on conditions",
                "color": "#EAB308",  # Yellow
                "config_schema": {
                    "column": {"type": "string", "required": True},
                    "operator": {
                        "type": "string",
                        "enum": ["contains", "equals", "not_equals", "greater_than", "less_than", "is_true", "is_false", "is_null", "is_not_null"],
                        "default": "contains",
                    },
                    "value": {"type": "string", "required": False},
                    "case_sensitive": {"type": "boolean", "default": False},
                },
            },
            {
                "type": BlockType.SAVE_CSV.value,
                "name": "Save CSV",
                "description": "Save the data to a CSV file",
                "color": "#22C55E",  # Green
                "config_schema": {
                    "file_name": {"type": "string", "default": "output.csv"}
                },
            },
        ]
    }


@app.post("/workflows/execute", response_model=WorkflowCreateResponse)
async def execute_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start executing a workflow.

    The workflow runs in the background. Use /workflows/{id}/status to check progress.
    """
    engine = get_engine()

    # Convert to dict format
    blocks = [
        {"id": b.id, "type": b.type, "config": b.config}
        for b in request.blocks
    ]

    # Create workflow
    workflow_id = engine.create_workflow(blocks)

    # Start execution in background
    async def run_workflow():
        await engine.execute_workflow(workflow_id, blocks)

    background_tasks.add_task(asyncio.create_task, run_workflow())

    return WorkflowCreateResponse(
        workflow_id=workflow_id,
        message="Workflow started",
    )


@app.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """Get the current status of a workflow."""
    engine = get_engine()
    state = engine.get_workflow_status(workflow_id)

    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowStatusResponse(
        workflow_id=state.workflow_id,
        status=state.status.value,
        blocks=[
            BlockProgressResponse(
                block_id=b.block_id,
                block_type=b.block_type.value,
                status=b.status.value,
                progress=b.progress,
                error=b.error,
            )
            for b in state.blocks
        ],
        current_block_index=state.current_block_index,
        error=state.error,
        result_preview=state.result_preview,
        result_columns=state.result_columns,
        result_row_count=state.result_row_count,
    )


@app.get("/workflows/{workflow_id}/results")
async def get_workflow_results(workflow_id: str):
    """Get the results of a completed workflow."""
    engine = get_engine()
    state = engine.get_workflow_status(workflow_id)

    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if state.status != WorkflowStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is {state.status.value}, not completed",
        )

    df = engine.get_workflow_result(workflow_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Results not found")

    return {
        "columns": list(df.columns),
        "row_count": len(df),
        "data": df.to_dict(orient="records"),
    }


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow and its data."""
    engine = get_engine()
    engine.cleanup_workflow(workflow_id)
    return {"message": "Workflow deleted"}


# File management endpoints
@app.get("/files", response_model=FileListResponse)
async def list_files():
    """List available CSV files."""
    files = []

    # List files in data directory
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith(".csv"):
                files.append(f)

    # Also check root directory for data.csv
    root_data = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.csv")
    if os.path.exists(root_data):
        files.append("data.csv")

    return FileListResponse(files=list(set(files)))


@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    file_path = os.path.join(DATA_DIR, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return {"filename": file.filename, "message": "File uploaded successfully"}


@app.get("/files/{filename}")
async def download_file(filename: str):
    """Download a CSV file."""
    # Check data directory first
    file_path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(file_path):
        # Check root directory
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            filename,
        )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=filename,
    )


@app.get("/files/{filename}/preview")
async def preview_file(filename: str, rows: int = 10):
    """Preview a CSV file."""
    import pandas as pd

    # Check data directory first
    file_path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(file_path):
        # Check root directory
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            filename,
        )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    df = pd.read_csv(file_path, nrows=rows)

    return {
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

