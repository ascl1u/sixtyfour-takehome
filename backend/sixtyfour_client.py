import os
import asyncio
import logging
from typing import Any, Optional
import httpx
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SIXTYFOUR_BASE_URL = "https://api.sixtyfour.ai"
DEFAULT_TIMEOUT = 900  # 15 minutes for sync calls
POLL_INTERVAL = 5  # seconds between status polls


@dataclass
class EnrichmentResult:
    """Result from an enrichment operation."""

    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class SixtyfourClient:
    """Client for interacting with the Sixtyfour API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SIXTYFOUR_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "SIXTYFOUR_API_KEY must be set in environment or passed to client"
            )

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def enrich_lead_async(
        self,
        lead_info: dict[str, Any],
        struct: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Submit an async lead enrichment job.

        Args:
            lead_info: Information about the lead (name, company, linkedin, etc.)
            struct: Dictionary of fields to enrich {field_name: description}

        Returns:
            task_id for polling status
        """
        payload = {"lead_info": lead_info}

        if struct:
            payload["struct"] = struct

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{SIXTYFOUR_BASE_URL}/enrich-lead-async",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("task_id", result.get("id", ""))

    async def get_job_status(self, task_id: str) -> dict[str, Any]:
        """
        Check the status of an async job.

        Returns:
            Dict with 'status' and optionally 'result' or 'error'
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SIXTYFOUR_BASE_URL}/job-status/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def wait_for_job(
        self,
        task_id: str,
        max_wait: int = 600,
        poll_interval: int = POLL_INTERVAL,
    ) -> EnrichmentResult:
        """
        Poll for job completion.

        Args:
            task_id: The task ID to poll
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between polls

        Returns:
            EnrichmentResult with the job result
        """
        elapsed = 0
        while elapsed < max_wait:
            status = await self.get_job_status(task_id)
            job_status = status.get("status", "").lower()

            if job_status in ("completed", "complete", "done", "success"):
                return EnrichmentResult(
                    success=True,
                    data=status.get("result", status.get("data", status)),
                )
            elif job_status in ("failed", "error"):
                logger.warning(f"Job {task_id} failed: {status.get('error')}")
                return EnrichmentResult(
                    success=False,
                    error=status.get("error", "Job failed"),
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"Job {task_id} timed out after {max_wait} seconds")
        return EnrichmentResult(
            success=False,
            error=f"Job timed out after {max_wait} seconds",
        )

    async def enrich_lead(
        self,
        lead_info: dict[str, Any],
        struct: Optional[dict[str, str]] = None,
    ) -> EnrichmentResult:
        """
        Enrich a lead (sync version - submits async and waits).

        Args:
            lead_info: Information about the lead
            struct: Dictionary of fields to enrich {field_name: description}

        Returns:
            EnrichmentResult with enriched data
        """
        try:
            task_id = await self.enrich_lead_async(lead_info, struct)
            return await self.wait_for_job(task_id)
        except httpx.HTTPStatusError as e:
            return EnrichmentResult(
                success=False,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}",
            )
        except Exception as e:
            return EnrichmentResult(success=False, error=str(e))

    async def find_email(
        self,
        lead: dict[str, Any],
        mode: str = "PROFESSIONAL",
    ) -> EnrichmentResult:
        """
        Find email address for a lead.

        Args:
            lead: Lead information (name, company, linkedin, etc.)
            mode: Email discovery mode (default: PROFESSIONAL)

        Returns:
            EnrichmentResult with found email
        """
        payload = {
            "lead": lead,
            "mode": mode,
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{SIXTYFOUR_BASE_URL}/find-email",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                return EnrichmentResult(success=True, data=result)
        except httpx.HTTPStatusError as e:
            return EnrichmentResult(
                success=False,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}",
            )
        except Exception as e:
            return EnrichmentResult(success=False, error=str(e))


# Singleton instance
_client: Optional[SixtyfourClient] = None


def get_client() -> SixtyfourClient:
    """Get or create the Sixtyfour client singleton."""
    global _client
    if _client is None:
        _client = SixtyfourClient()
    return _client

