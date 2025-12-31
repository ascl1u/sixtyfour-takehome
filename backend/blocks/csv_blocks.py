import os
from typing import Any, Optional, Callable
import pandas as pd
import aiofiles
import asyncio

from blocks.base import Block, BlockType


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


class ReadCSVBlock(Block):
    """Block to read a CSV file into a DataFrame."""

    block_type = BlockType.READ_CSV

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Read a CSV file.

        Config:
            file_path: Path to the CSV file to read
        """
        file_path = config.get("file_path", "")

        if not file_path:
            raise ValueError("file_path is required for ReadCSV block")

        # Check if it's a relative path and resolve it
        if not os.path.isabs(file_path):
            # Try data directory first, then current directory
            data_path = os.path.join(DATA_DIR, file_path)
            if os.path.exists(data_path):
                file_path = data_path
            elif not os.path.exists(file_path):
                # Try root directory
                root_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    file_path,
                )
                if os.path.exists(root_path):
                    file_path = root_path

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        if on_progress:
            await on_progress(10)

        # Read CSV using pandas (run in executor to not block)
        loop = asyncio.get_event_loop()
        result_df = await loop.run_in_executor(None, pd.read_csv, file_path)

        if on_progress:
            await on_progress(100)

        return result_df


class SaveCSVBlock(Block):
    """Block to save a DataFrame to a CSV file."""

    block_type = BlockType.SAVE_CSV

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Save DataFrame to a CSV file.

        Config:
            file_name: Name of the output file (will be saved in data directory)
        """
        if df is None:
            raise ValueError("No DataFrame to save")

        file_name = config.get("file_name", "output.csv")

        # Ensure file name ends with .csv
        if not file_name.endswith(".csv"):
            file_name += ".csv"

        output_path = os.path.join(DATA_DIR, file_name)

        if on_progress:
            await on_progress(10)

        # Save CSV using pandas (run in executor to not block)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: df.to_csv(output_path, index=False)
        )

        if on_progress:
            await on_progress(100)

        return df

