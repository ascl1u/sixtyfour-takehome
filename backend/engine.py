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
    PauseException,
    ReadCSVBlock,
    SaveCSVBlock,
    FilterBlock,
    EnrichLeadBlock,
    FindEmailBlock,
)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class BlockStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
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
    # Pause/resume control fields
    pause_requested: bool = False
    last_processed_row: int = 0  # Row index to resume from
    blocks_config: Optional[list[dict]] = None  # Store blocks config for resume


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
        start_block_index: int = 0,
        start_row: int = 0,
    ) -> WorkflowState:
        """
        Execute a workflow.

        Args:
            workflow_id: The workflow ID
            blocks: List of block definitions with 'id', 'type', and 'config'
            start_block_index: Block index to start from (for resume)
            start_row: Row index to start from within the block (for resume)

        Returns:
            Final WorkflowState
        """
        state = self.workflows.get(workflow_id)
        if not state:
            raise ValueError(f"Workflow {workflow_id} not found")

        state.status = WorkflowStatus.RUNNING
        state.pause_requested = False  # Reset pause flag
        state.blocks_config = blocks  # Store for potential resume
        
        if state.started_at is None:
            state.started_at = datetime.utcnow()

        # Get current DataFrame if resuming
        current_df: Optional[pd.DataFrame] = self._dataframes.get(workflow_id)

        # Create pause check callback
        def pause_check() -> bool:
            return state.pause_requested

        try:
            for i, block_def in enumerate(blocks):
                # Skip completed blocks when resuming
                if i < start_block_index:
                    continue
                    
                block_type = BlockType(block_def["type"])
                config = block_def.get("config", {})

                # Update state
                state.current_block_index = i
                block_progress = state.blocks[i]
                block_progress.status = BlockStatus.RUNNING
                if block_progress.started_at is None:
                    block_progress.started_at = datetime.utcnow()

                # Create progress callback
                async def on_progress(progress: int):
                    block_progress.progress = progress

                # Get block class and instantiate
                block_class = BLOCK_CLASSES.get(block_type)
                if not block_class:
                    raise ValueError(f"Unknown block type: {block_type}")

                block = block_class()

                # Determine start row for this block
                block_start_row = start_row if i == start_block_index else 0

                # Execute block with pause support
                current_df = await block.execute(
                    current_df, 
                    config, 
                    on_progress,
                    pause_check,
                    block_start_row,
                )

                # Update block status
                block_progress.status = BlockStatus.COMPLETED
                block_progress.progress = 100
                block_progress.completed_at = datetime.utcnow()

                # Store intermediate result
                if current_df is not None:
                    self._dataframes[workflow_id] = current_df
                    state.result_columns = list(current_df.columns)
                    state.result_row_count = len(current_df)
                    preview_df = current_df.head(10).copy()
                    state.result_preview = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")
                    
                # Reset start_row for subsequent blocks
                start_row = 0

            # Workflow completed successfully
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow()

        except PauseException as pe:
            # Handle pause - save state for resume
            print(f"[Engine] WORKFLOW PAUSED at block {state.current_block_index}, row {pe.last_processed_row}")
            print(f"[Engine] Partial results: {pe.partial_df is not None and len(pe.partial_df) or 0} rows available")
            state.status = WorkflowStatus.PAUSED
            state.last_processed_row = pe.last_processed_row
            
            # Store partial DataFrame
            if pe.partial_df is not None:
                self._dataframes[workflow_id] = pe.partial_df
                state.result_columns = list(pe.partial_df.columns)
                state.result_row_count = len(pe.partial_df)
                preview_df = pe.partial_df.head(10).copy()
                state.result_preview = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")

            # Mark current block as paused
            if state.current_block_index < len(state.blocks):
                state.blocks[state.current_block_index].status = BlockStatus.PAUSED

        except Exception as e:
            state.status = WorkflowStatus.FAILED
            state.error = str(e)
            state.completed_at = datetime.utcnow()

            # Mark current block as failed
            if state.current_block_index < len(state.blocks):
                state.blocks[state.current_block_index].status = BlockStatus.FAILED
                state.blocks[state.current_block_index].error = str(e)

        return state
    
    async def resume_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Resume a paused workflow from where it stopped.
        
        Returns:
            The WorkflowState after resuming, or None if workflow not found or not paused.
        """
        state = self.workflows.get(workflow_id)
        if not state:
            return None
        
        if state.status != WorkflowStatus.PAUSED:
            return None
        
        if not state.blocks_config:
            return None
        
        # Resume from the paused block and row
        print(f"[Engine] RESUMING workflow {workflow_id} from block {state.current_block_index}, row {state.last_processed_row}")
        return await self.execute_workflow(
            workflow_id,
            state.blocks_config,
            start_block_index=state.current_block_index,
            start_row=state.last_processed_row,
        )

    def cleanup_workflow(self, workflow_id: str) -> None:
        """Remove a workflow and its data from memory."""
        self.workflows.pop(workflow_id, None)
        self._dataframes.pop(workflow_id, None)

    def request_pause(self, workflow_id: str) -> bool:
        """
        Request to pause a running workflow.
        
        Returns:
            True if pause was requested successfully, False if workflow not found or not running.
        """
        state = self.workflows.get(workflow_id)
        if not state:
            return False
        
        if state.status != WorkflowStatus.RUNNING:
            return False
        
        state.pause_requested = True
        print(f"[Engine] PAUSE REQUESTED for workflow {workflow_id} - will pause after current batch")
        return True

    def is_pause_requested(self, workflow_id: str) -> bool:
        """Check if pause has been requested for a workflow."""
        state = self.workflows.get(workflow_id)
        return state.pause_requested if state else False


# Singleton engine instance
_engine: Optional[WorkflowEngine] = None


def get_engine() -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine

