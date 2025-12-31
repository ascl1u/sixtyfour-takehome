from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Callable
import pandas as pd


class BlockType(str, Enum):
    READ_CSV = "read_csv"
    SAVE_CSV = "save_csv"
    FILTER = "filter"
    ENRICH_LEAD = "enrich_lead"
    FIND_EMAIL = "find_email"


class PauseException(Exception):
    """
    Exception raised when a block execution is paused.
    
    Carries the partial result and resume state for later continuation.
    """
    
    def __init__(
        self,
        partial_df: pd.DataFrame,
        last_processed_row: int,
        message: str = "Workflow paused"
    ):
        super().__init__(message)
        self.partial_df = partial_df
        self.last_processed_row = last_processed_row


class Block(ABC):
    """Base class for all workflow blocks."""

    block_type: BlockType

    @abstractmethod
    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Execute the block's operation.

        Args:
            df: Input DataFrame (may be None for source blocks like ReadCSV)
            config: Block-specific configuration
            on_progress: Optional callback for progress updates (0-100)
            pause_check: Optional callback that returns True if pause is requested
            start_row: Row index to start processing from (for resume)

        Returns:
            Resulting DataFrame after block execution
            
        Raises:
            PauseException: If pause is requested, contains partial results
        """
        pass

    @classmethod
    def get_block_type(cls) -> BlockType:
        return cls.block_type

