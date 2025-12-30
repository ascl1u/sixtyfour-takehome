import asyncio
import uuid
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd

from blocks import (
    Block,
    BlockType,
    ReadCSVBlock,
    SaveCSVBlock,
    FilterBlock,
    EnrichLeadBlock,
    FindEmailBlock,
)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BlockStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BlockProgress:
    """Progress information for a single block."""

    block_id: str
    block_type: BlockType
    status: BlockStatus = BlockStatus.PENDING
    progress: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowState:
    """State of a workflow execution."""

    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    blocks: list[BlockProgress] = field(default_factory=list)
    current_block_index: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_preview: Optional[list[dict]] = None
    result_columns: Optional[list[str]] = None
    result_row_count: int = 0


# Block type to class mapping
BLOCK_CLASSES: dict[BlockType, type[Block]] = {
    BlockType.READ_CSV: ReadCSVBlock,
    BlockType.SAVE_CSV: SaveCSVBlock,
    BlockType.FILTER: FilterBlock,
    BlockType.ENRICH_LEAD: EnrichLeadBlock,
    BlockType.FIND_EMAIL: FindEmailBlock,
}


class WorkflowEngine:
    """Engine for executing workflows."""

    def __init__(self):
        self.workflows: dict[str, WorkflowState] = {}
        self._dataframes: dict[str, pd.DataFrame] = {}

    def create_workflow(
        self, blocks: list[dict[str, Any]]
    ) -> str:
        """
        Create a new workflow.

        Args:
            blocks: List of block definitions with 'id', 'type', and 'config'

        Returns:
            workflow_id
        """
        workflow_id = str(uuid.uuid4())

        block_progress = []
        for block_def in blocks:
            block_progress.append(
                BlockProgress(
                    block_id=block_def.get("id", str(uuid.uuid4())),
                    block_type=BlockType(block_def["type"]),
                )
            )

        self.workflows[workflow_id] = WorkflowState(
            workflow_id=workflow_id,
            blocks=block_progress,
        )

        return workflow_id

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get the current status of a workflow."""
        return self.workflows.get(workflow_id)

    def get_workflow_result(self, workflow_id: str) -> Optional[pd.DataFrame]:
        """Get the result DataFrame of a completed workflow."""
        return self._dataframes.get(workflow_id)

    async def execute_workflow(
        self,
        workflow_id: str,
        blocks: list[dict[str, Any]],
    ) -> WorkflowState:
        """
        Execute a workflow.

        Args:
            workflow_id: The workflow ID
            blocks: List of block definitions with 'id', 'type', and 'config'

        Returns:
            Final WorkflowState
        """
        state = self.workflows.get(workflow_id)
        if not state:
            raise ValueError(f"Workflow {workflow_id} not found")

        state.status = WorkflowStatus.RUNNING
        state.started_at = datetime.utcnow()

        current_df: Optional[pd.DataFrame] = None

        try:
            for i, block_def in enumerate(blocks):
                block_id = block_def.get("id", str(uuid.uuid4()))
                block_type = BlockType(block_def["type"])
                config = block_def.get("config", {})

                # Update state
                state.current_block_index = i
                block_progress = state.blocks[i]
                block_progress.status = BlockStatus.RUNNING
                block_progress.started_at = datetime.utcnow()

                # Create progress callback
                async def on_progress(progress: int):
                    block_progress.progress = progress

                # Get block class and instantiate
                block_class = BLOCK_CLASSES.get(block_type)
                if not block_class:
                    raise ValueError(f"Unknown block type: {block_type}")

                block = block_class()

                # Execute block
                current_df = await block.execute(current_df, config, on_progress)

                # Update block status
                block_progress.status = BlockStatus.COMPLETED
                block_progress.progress = 100
                block_progress.completed_at = datetime.utcnow()

                # Store intermediate result preview
                if current_df is not None:
                    state.result_columns = list(current_df.columns)
                    state.result_row_count = len(current_df)
                    state.result_preview = current_df.head(10).to_dict(orient="records")

            # Workflow completed successfully
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow()

            # Store final DataFrame
            if current_df is not None:
                self._dataframes[workflow_id] = current_df

        except Exception as e:
            state.status = WorkflowStatus.FAILED
            state.error = str(e)
            state.completed_at = datetime.utcnow()

            # Mark current block as failed
            if state.current_block_index < len(state.blocks):
                state.blocks[state.current_block_index].status = BlockStatus.FAILED
                state.blocks[state.current_block_index].error = str(e)

        return state

    def cleanup_workflow(self, workflow_id: str) -> None:
        """Remove a workflow and its data from memory."""
        self.workflows.pop(workflow_id, None)
        self._dataframes.pop(workflow_id, None)


# Singleton engine instance
_engine: Optional[WorkflowEngine] = None


def get_engine() -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine

