from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
import pandas as pd


class BlockType(str, Enum):
    READ_CSV = "read_csv"
    SAVE_CSV = "save_csv"
    FILTER = "filter"
    ENRICH_LEAD = "enrich_lead"
    FIND_EMAIL = "find_email"


class Block(ABC):
    """Base class for all workflow blocks."""

    block_type: BlockType

    @abstractmethod
    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[callable] = None,
    ) -> pd.DataFrame:
        """
        Execute the block's operation.

        Args:
            df: Input DataFrame (may be None for source blocks like ReadCSV)
            config: Block-specific configuration
            on_progress: Optional callback for progress updates (0-100)

        Returns:
            Resulting DataFrame after block execution
        """
        pass

    @classmethod
    def get_block_type(cls) -> BlockType:
        return cls.block_type

