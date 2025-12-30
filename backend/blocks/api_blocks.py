import asyncio
from typing import Any, Optional
import pandas as pd

from blocks.base import Block, BlockType
from sixtyfour_client import get_client, EnrichmentResult


class EnrichLeadBlock(Block):
    """Block to enrich lead information using Sixtyfour API."""

    block_type = BlockType.ENRICH_LEAD

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[callable] = None,
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

        struct = config.get("struct", [])
        name_col = config.get("name_column", "name")
        company_col = config.get("company_column", "company")
        linkedin_col = config.get("linkedin_column", "linkedin")
        max_concurrent = config.get("max_concurrent", 10)

        # Semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

        total_rows = len(df)
        completed = 0
        results = []

        async def enrich_row(idx: int, row: pd.Series) -> tuple[int, EnrichmentResult]:
            nonlocal completed
            async with semaphore:
                lead_info = {}

                if name_col in row and pd.notna(row[name_col]):
                    lead_info["name"] = str(row[name_col])
                if company_col in row and pd.notna(row[company_col]):
                    lead_info["company"] = str(row[company_col])
                if linkedin_col in row and pd.notna(row[linkedin_col]):
                    lead_info["linkedin"] = str(row[linkedin_col])

                # Add any additional context from the row
                if "email" in row and pd.notna(row["email"]):
                    lead_info["email"] = str(row["email"])
                if "company_location" in row and pd.notna(row["company_location"]):
                    lead_info["location"] = str(row["company_location"])

                result = await client.enrich_lead(lead_info, struct if struct else None)

                completed += 1
                if on_progress:
                    progress = int((completed / total_rows) * 100)
                    await on_progress(progress)

                return idx, result

        # Submit all enrichment tasks
        tasks = [enrich_row(idx, row) for idx, row in df.iterrows()]
        results = await asyncio.gather(*tasks)

        # Create a copy of the DataFrame to add enrichment data
        result_df = df.copy()

        # Add enrichment results to DataFrame
        for idx, enrichment_result in results:
            if enrichment_result.success and enrichment_result.data:
                data = enrichment_result.data
                # Add each field from the enrichment result as a new column
                for key, value in data.items():
                    if key not in ["success", "error"]:
                        col_name = f"enriched_{key}"
                        if col_name not in result_df.columns:
                            result_df[col_name] = None
                        result_df.at[idx, col_name] = value

        return result_df


class FindEmailBlock(Block):
    """Block to find email addresses using Sixtyfour API."""

    block_type = BlockType.FIND_EMAIL

    async def execute(
        self,
        df: Optional[pd.DataFrame],
        config: dict[str, Any],
        on_progress: Optional[callable] = None,
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

        # Semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

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
        completed = 0

        async def find_email_for_row(
            idx: int, row: pd.Series
        ) -> tuple[int, EnrichmentResult]:
            nonlocal completed
            async with semaphore:
                lead = {}

                if name_col in row and pd.notna(row[name_col]):
                    lead["name"] = str(row[name_col])
                if company_col in row and pd.notna(row[company_col]):
                    lead["company"] = str(row[company_col])
                if linkedin_col in row and pd.notna(row[linkedin_col]):
                    lead["linkedin"] = str(row[linkedin_col])

                result = await client.find_email(lead, mode)

                completed += 1
                if on_progress:
                    progress = int((completed / total_rows) * 100)
                    await on_progress(progress)

                return idx, result

        # Submit all email lookup tasks
        tasks = [find_email_for_row(idx, row) for idx, row in rows_to_process]
        results = await asyncio.gather(*tasks)

        # Add results to DataFrame
        for idx, email_result in results:
            if email_result.success and email_result.data:
                email = email_result.data.get("email", email_result.data.get("found_email"))
                if email:
                    result_df.at[idx, output_col] = email

        return result_df

