from typing import Any, Optional, Callable
import pandas as pd

from blocks.base import Block, BlockType


class FilterBlock(Block):
    """Block to filter DataFrame rows based on conditions."""

    block_type = BlockType.FILTER

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Filter DataFrame rows based on a condition.

        Config:
            column: Column name to filter on
            operator: One of 'contains', 'equals', 'not_equals', 'greater_than', 
                      'less_than', 'is_true', 'is_false', 'is_null', 'is_not_null'
            value: Value to compare against (not needed for is_true, is_false, 
                   is_null, is_not_null)
            case_sensitive: Boolean for string operations (default: False)
        """
        if df is None:
            raise ValueError("No DataFrame to filter")

        column = config.get("column")
        operator = config.get("operator", "contains")
        value = config.get("value", "")
        case_sensitive = config.get("case_sensitive", False)

        if not column:
            raise ValueError("column is required for Filter block")

        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")

        if on_progress:
            await on_progress(10)

        # Apply filter based on operator
        if operator == "contains":
            if case_sensitive:
                mask = df[column].astype(str).str.contains(str(value), na=False)
            else:
                mask = df[column].astype(str).str.contains(
                    str(value), case=False, na=False
                )
        elif operator == "equals":
            mask = df[column] == value
        elif operator == "not_equals":
            mask = df[column] != value
        elif operator == "greater_than":
            mask = df[column] > value
        elif operator == "less_than":
            mask = df[column] < value
        elif operator == "is_true":
            mask = df[column] == True
        elif operator == "is_false":
            mask = df[column] == False
        elif operator == "is_null":
            mask = df[column].isna()
        elif operator == "is_not_null":
            mask = df[column].notna()
        else:
            raise ValueError(f"Unknown operator: {operator}")

        result_df = df[mask].copy()

        if on_progress:
            await on_progress(100)

        return result_df

