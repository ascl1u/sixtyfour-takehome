import asyncio
from typing import Any, Optional, Callable
import pandas as pd

from blocks.base import Block, BlockType, PauseException
from sixtyfour_client import get_client, EnrichmentResult


class EnrichLeadBlock(Block):
    """Block to enrich lead information using Sixtyfour API."""

    block_type = BlockType.ENRICH_LEAD

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Enrich leads in the DataFrame.

        Config:
            struct: List of fields to enrich, e.g.:
                [{"name": "education", "description": "Educational background"}]
            name_column: Column containing person's name (default: "name")
            company_column: Column containing company name (default: "company")
            linkedin_column: Column containing LinkedIn URL (default: "linkedin")
            max_concurrent: Max concurrent API calls (default: 10)
        """
        if df is None or len(df) == 0:
            raise ValueError("No DataFrame or empty DataFrame to enrich")

        client = get_client()

        # Convert struct from array format to dict format for API
        struct_config = config.get("struct", [])
        struct: dict[str, str] = {}
        if isinstance(struct_config, list):
            for item in struct_config:
                if isinstance(item, dict) and "name" in item:
                    struct[item["name"]] = item.get("description", "")
        elif isinstance(struct_config, dict):
            struct = struct_config

        name_col = config.get("name_column", "name")
        company_col = config.get("company_column", "company")
        linkedin_col = config.get("linkedin_column", "linkedin")
        max_concurrent = config.get("max_concurrent", 1)
        batch_size = config.get("batch_size", max_concurrent)

        # Create result DataFrame
        result_df = df.copy()
        
        # Get rows to process (from start_row onwards)
        rows_list = list(df.iterrows())
        total_rows = len(rows_list)
        
        # Process rows in batches for pause support
        current_row = start_row
        print(f"[EnrichLead] Starting enrichment: {total_rows} rows, batch_size={batch_size}")
        
        while current_row < total_rows:
            print(f"[EnrichLead] Processing batch starting at row {current_row}/{total_rows} - PAUSE AVAILABLE NOW")
            
            # Check for pause before starting a new batch
            if pause_check and pause_check():
                print(f"[EnrichLead] PAUSING at row {current_row}/{total_rows}")
                raise PauseException(
                    partial_df=result_df,
                    last_processed_row=current_row,
                    message=f"Paused at row {current_row}/{total_rows}"
                )
            
            # Determine batch end
            batch_end = min(current_row + batch_size, total_rows)
            batch_rows = rows_list[current_row:batch_end]
            
            # Process batch concurrently
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def enrich_row(idx: int, row: pd.Series) -> tuple[int, EnrichmentResult]:
                async with semaphore:
                    lead_info = {}

                    if name_col in row and pd.notna(row[name_col]):
                        lead_info["name"] = str(row[name_col])
                    if company_col in row and pd.notna(row[company_col]):
                        lead_info["company"] = str(row[company_col])
                    if linkedin_col in row and pd.notna(row[linkedin_col]):
                        lead_info["linkedin"] = str(row[linkedin_col])

                    if "email" in row and pd.notna(row["email"]):
                        lead_info["email"] = str(row["email"])
                    if "company_location" in row and pd.notna(row["company_location"]):
                        lead_info["location"] = str(row["company_location"])

                    result = await client.enrich_lead(lead_info, struct if len(struct) > 0 else None)
                    return idx, result

            # Submit batch tasks
            tasks = [enrich_row(idx, row) for idx, row in batch_rows]
            results = await asyncio.gather(*tasks)

            # Add batch results to DataFrame
            for idx, enrichment_result in results:
                if enrichment_result.success and enrichment_result.data:
                    data = enrichment_result.data
                    for key, value in data.items():
                        if key not in ["success", "error"]:
                            col_name = f"enriched_{key}"
                            if col_name not in result_df.columns:
                                result_df[col_name] = None
                            result_df.at[idx, col_name] = value

            # Update progress
            current_row = batch_end
            print(f"[EnrichLead] Completed batch: {current_row}/{total_rows} rows done ({int((current_row / total_rows) * 100)}%)")
            if on_progress:
                progress = int((current_row / total_rows) * 100)
                await on_progress(progress)

        print(f"[EnrichLead] COMPLETED: All {total_rows} rows enriched")
        return result_df


class FindEmailBlock(Block):
    """Block to find email addresses using Sixtyfour API."""

    block_type = BlockType.FIND_EMAIL

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[Callable[[int], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        start_row: int = 0,
    ) -> pd.DataFrame:
        """
        Find email addresses for leads in the DataFrame.

        Config:
            mode: Email discovery mode (default: "PROFESSIONAL")
            name_column: Column containing person's name (default: "name")
            company_column: Column containing company name (default: "company")
            linkedin_column: Column containing LinkedIn URL (default: "linkedin")
            output_column: Column to store found email (default: "found_email")
            skip_existing: Skip rows that already have email (default: True)
            max_concurrent: Max concurrent API calls (default: 10)
        """
        if df is None or len(df) == 0:
            raise ValueError("No DataFrame or empty DataFrame")

        client = get_client()

        mode = config.get("mode", "PROFESSIONAL")
        name_col = config.get("name_column", "name")
        company_col = config.get("company_column", "company")
        linkedin_col = config.get("linkedin_column", "linkedin")
        output_col = config.get("output_column", "found_email")
        skip_existing = config.get("skip_existing", True)
        max_concurrent = config.get("max_concurrent", 10)
        batch_size = config.get("batch_size", max_concurrent)

        result_df = df.copy()
        if output_col not in result_df.columns:
            result_df[output_col] = None

        # Determine which rows need email lookup
        rows_to_process = []
        for idx, row in df.iterrows():
            if skip_existing and "email" in row and pd.notna(row["email"]) and row["email"]:
                result_df.at[idx, output_col] = row["email"]
            else:
                rows_to_process.append((idx, row))

        if not rows_to_process:
            if on_progress:
                await on_progress(100)
            return result_df

        total_rows = len(rows_to_process)
        print(f"[FindEmail] Starting email lookup: {total_rows} rows to process, batch_size={batch_size}")
        
        # Adjust start_row to be relative to rows_to_process
        current_row = start_row
        
        while current_row < total_rows:
            print(f"[FindEmail] Processing batch starting at row {current_row}/{total_rows} - PAUSE AVAILABLE NOW")
            
            # Check for pause before starting a new batch
            if pause_check and pause_check():
                print(f"[FindEmail] PAUSING at row {current_row}/{total_rows}")
                raise PauseException(
                    partial_df=result_df,
                    last_processed_row=current_row,
                    message=f"Paused at row {current_row}/{total_rows}"
                )
            
            # Determine batch end
            batch_end = min(current_row + batch_size, total_rows)
            batch_rows = rows_to_process[current_row:batch_end]
            
            # Process batch concurrently
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def find_email_for_row(
                idx: int, row: pd.Series
            ) -> tuple[int, EnrichmentResult]:
                async with semaphore:
                    lead = {}

                    if name_col in row and pd.notna(row[name_col]):
                        lead["name"] = str(row[name_col])
                    if company_col in row and pd.notna(row[company_col]):
                        lead["company"] = str(row[company_col])
                    if linkedin_col in row and pd.notna(row[linkedin_col]):
                        lead["linkedin"] = str(row[linkedin_col])

                    result = await client.find_email(lead, mode)
                    return idx, result

            # Submit batch tasks
            tasks = [find_email_for_row(idx, row) for idx, row in batch_rows]
            results = await asyncio.gather(*tasks)

            # Add results to DataFrame
            for idx, email_result in results:
                if email_result.success and email_result.data:
                    email = email_result.data.get("email", email_result.data.get("found_email"))
                    if email:
                        result_df.at[idx, output_col] = email

            # Update progress
            current_row = batch_end
            print(f"[FindEmail] Completed batch: {current_row}/{total_rows} rows done ({int((current_row / total_rows) * 100)}%)")
            if on_progress:
                progress = int((current_row / total_rows) * 100)
                await on_progress(progress)

        print(f"[FindEmail] COMPLETED: All {total_rows} emails found")
        return result_df

